import datetime
import json
import os
import re
from time import time, sleep
from uuid import uuid4

from google.cloud import language_v1

import openai
import pinecone

credentials = 'careful-voyage-380603-675da19bbd85.json'
client = language_v1.LanguageServiceClient.from_service_account_json(credentials)


# The next 4 methods are for loading and saving files.
def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def save_json(filepath, payload):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)


# Gets the current time in a readable format.
def timestamp_to_datetime(unix_time):
    return datetime.datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")


# Creates embeddings for the message and the response.
def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII', errors='ignore').decode()  # fix any UNICODE errors
    response = openai.Embedding.create(input=content, engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector


# Generates a response using GPT-3.
def gpt3_completion(prompt, engine='text-davinci-003', temp=2.0, top_p=1.0, tokens=400, freq_pen=1.0, pres_pen=0.5,
                    stop=None):
    if stop is None:
        stop = ['USER:', 'AIMEE:']
    max_retry = 5
    retry = 0
    prompt = prompt.encode(encoding='ASCII', errors='ignore').decode()
    while True:
        try:
            response = openai.Completion.create(
                engine=engine,
                prompt=prompt,
                temperature=temp,
                max_tokens=tokens,
                top_p=top_p,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                stop=stop)
            text = response['choices'][0]['text'].strip()
            text = re.sub('[\r\n]+', '\n', text)
            text = re.sub('[\t ]+', ' ', text)
            filename = '%s_gpt3.txt' % time()
            if not os.path.exists('gpt3_logs'):
                os.makedirs('gpt3_logs')
            save_file('gpt3_logs/%s' % filename, prompt + '\n\n==========\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            sleep(1)


# Loads previous conversations from the Pinecone database.
def load_conversation(results):
    result = list()
    for m in results['matches']:
        info = load_json('nexus/%s.json' % m['id'])
        result.append(info)
    ordered = sorted(result, key=lambda d: d['time'], reverse=False)  # sort them all chronologically
    messages = [i['message'] for i in ordered]
    return '\n'.join(messages).strip()


# Analyzes the sentiment of the message using Google Natural Language API.
def analyze_sentiment(message):
    document = language_v1.Document(content=message, type_=language_v1.Document.Type.PLAIN_TEXT)
    sentiment = client.analyze_sentiment(request={'document': document}).document_sentiment
    return sentiment.score


# Gets the Pinecone index.
def get_index():
    pinecone.init(api_key=open_file('key_pinecone.txt'), environment='us-west4-gcp')
    vdb = pinecone.Index("aimee")
    return vdb


# This is the main method that generates a response and creates embeddings. It returns the bots response.
def response_and_index(message, author) -> str:
    pinecone.init(api_key=open_file('key_pinecone.txt'), environment='us-west4-gcp')
    sentiment_score = analyze_sentiment(message)
    print('on_message called!')
    convo_length = 30
    openai.api_key = open_file('key_openai.txt')
    print('open api key found')
    pinecone.init(api_key=open_file('key_pinecone.txt'), environment='us-west4-gcp')
    print('pinecone key found')
    vdb = pinecone.Index("aimee")
    print('index selected')
    payload = list()
    print('a is now the message content')
    timestamp = time()
    timestring = timestamp_to_datetime(timestamp)
    print('message is now a')
    vector = gpt3_embedding(message)
    print('embedding created')
    print(vector)
    unique_id = str(uuid4())
    metadata = {'speaker': author, 'time': timestamp, 'message': message, 'timestring': timestring,
                'uuid': unique_id}
    save_json('nexus/' + unique_id + '.json', metadata)
    print('saving json')
    payload.append((unique_id, vector))

    results = vdb.query(vector=vector, top_k=convo_length)
    print(results)
    conversation = load_conversation(results)
    print('conversation loaded')
    prompt = open_file('prompt_response.txt').replace('<<CONVERSATION>>', conversation).replace('<<MESSAGE>>', message) \
        .replace('<<USER>>', author).replace('<<SCORE>>', str(sentiment_score))
    print('prompt created')
    print(prompt)

    output = gpt3_completion(prompt)
    print('output created')
    timestamp = time()
    timestring = timestamp_to_datetime(timestamp)
    vector = gpt3_embedding(output)
    print('vector created')
    unique_id = str(uuid4())
    metadata = {'speaker': 'Aimee', 'time': timestamp, 'message': output, 'timestring': timestring,
                'uuid': unique_id}
    save_json('nexus/' + unique_id + '.json', metadata)
    payload.append((unique_id, vector))
    vdb.upsert(payload)
    print('upserted')
    return output
