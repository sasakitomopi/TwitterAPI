# Project : Twitter API
# 特定ユーザーのツイート内容、いいね数、リツイート数などをGoogleスプレッドシートに自動取得する

# pandas
# Twitter APIからのJSONペイロード応答の表形式への変換

# gspred
# Googleスプレッドシートへの接続

# requests
# HTTPリクエストを行うためのTwitter APIへの接続

# 0auth2client
# サービスアカウントを使った認証のサポートに使用

import pandas as pd
import gspread
import os
import requests

from oauth2client.service_account import ServiceAccountCredentials

def connect_to_twitter():
    bearer_token = os.environ.get('BEARER_TOKEN')
    return {"Authorization" : "Bearer {}".format(bearer_token)}

def make_request(headers ,username):
    url = 'https://api.twitter.com/2/users/by/username/' + username
    response = requests.request("GET",url,headers = headers).json()
    return response["data"]["id"]

def get_recent_tweets(headers,searchId,max_results=10,next_token=""):
    url = 'https://api.twitter.com/2/users/' + searchId + '/tweets'
    if int(max_results)<5:
        max_results = 5
    
    if next_token=="":
        params = {
            "tweet.fields" : "created_at,public_metrics",
            "max_results":int(max_results),
        }
    else:
        params = {
            "tweet.fields" : "created_at,public_metrics",
            "max_results":int(max_results),
            "pagination_token":next_token
        }

    response=requests.request("GET",url,headers=headers,params=params).json()
    next_token=response['meta']['next_token']

    return response,next_token

# JSON形式のデータをスプレッドシートで受け取れるようpandasを利用する関数を定義
def make_df(response):
    df = pd.json_normalize(response["data"])
    df = df.rename(columns= {'public_metrics.retweet_count': 'retweet', 
                        'public_metrics.reply_count': 'reply',
                        'public_metrics.like_count':'like',
                        'public_metrics.quote_count':'quote'})
    return df

def authenticate_to_google():
    scope = [
        "https://spreadsheets.google.com/feeds"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "/path/to/your/file.json", scope
    )
    return credentials

if __name__ == "__main__":
    #必要なパラメーターの入力
    username = input("Which user's tweets do you want to retrive? ex. @nikkei -> nikkei:")
    max_tweets = input("How many tweets do you want to retrive? (min=5):")
    print("This tool may return different number tweets you want because the minimum permitted value for get_tweets api is 5")

    #Twitterからのデータ取得
    headers = connect_to_twitter()
    userid = (make_request(headers,username))
    #APIの仕様上、get_recent_tweetsで一回で取得できるツイート数が10ツイートなので、max_tweetsが10以上の場合は、next tokenを取得して、必要な回数取得し続けるようにしています。それでも上限は3,200ツイートのようです。
    #(ref) https://developer.twitter.com/en/docs/twitter-api/tweets/timelines/api-reference/get-users-id-tweets

    if int(max_tweets) <= 10:
        response,next_token = get_recent_tweets(headers,userid,max_results=int(max_tweets))
        df = make_df(response)
    else:
        response,next_token = get_recent_tweets(headers,userid,max_results=10)
        df = make_df(response)
        tweets_count = int(max_tweets)-10
        while tweets_count > 0:
            if tweets_count < 10:
                max_results = tweets_count
            else:
                max_results = 10
                response,next_token = get_recent_tweets(headers,userid,max_results=max_results,next_token=next_token)
                df_new = make_df(response)
                df = pd.concat([df,df_new])
                tweets_count = tweets_count - 10

    #Googleスプレッドシートへのデータアップロード
    credentials = authenticate_to_google()
    gc = gspread.authorize(credentials)
    workbook = gc.open_by_key("spreadsheet_id")
    sheet = workbook.worksheet("Sheet1")
    sheet.clear()
    sheet.update("A1",[df.columns.values.tolist()] + df.values.tolist())
    print("Please check https://docs.google.com/spreadsheets/d/spreadsheet_id")

