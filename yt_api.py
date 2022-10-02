# For data analysis and deployment
import streamlit as st
import pandas as pd
import plotly.express as px

#For Youtube API calls
from googleapiclient.discovery import build
import collections
from dateutil import parser
import isodate

#Convert repeating zeroes to symbols
from numerize import numerize as n

#For web scraping youtuber's channel id and logo
import re
import json
import requests
from bs4 import BeautifulSoup

from PIL import Image

st.set_page_config(
   page_title="YT St-Board",
   page_icon=":bar_chart:",
   layout="wide"
#    initial_sidebar_state="expanded",
)

API_KEY = "AIzaSyCaNVP6p46lLpeVMxAED5rrmJUC6n7PvOg"

api_service_name = "youtube"
api_version = "v3"

st.title("Youtuber's Streamlit Dashboard")

with st.expander('About the Creator'):
    st.write("""
    # Hello, I'm JP Curada!
    ### A Python and Data Science Enthusiast

    Twitter: https://twitter.com/jpcodesss_

    I am open for constructive criticisms and your feedback will be highly appreciated.

    Gmail: j.curada02@gmail.com
    """)


st.markdown("---")

youtube = build(
    api_service_name, api_version, developerKey=API_KEY, cache_discovery=False)

@st.cache

def get_channel_id_logo(URL):

    soup = BeautifulSoup(requests.get(URL, cookies={"CONSENT":"YES+1"}).text, "html.parser")

    data = re.search(r"var ytInitialData = ({.*});", str(soup.prettify())).group(1)
    json_data = json.loads(data)

    channel_id = [json_data['header']['c4TabbedHeaderRenderer']['channelId']]
    channel_logo = json_data['header']['c4TabbedHeaderRenderer']['avatar']['thumbnails'][2]['url']

    return channel_id, channel_logo

def get_channel_stats(youtube, channel_ids):
    
    all_data = []
    
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=','.join(channel_ids)
    )
    response = request.execute()

    #loop through items
    for item in response['items']:
        data = {'channelName':item['snippet']['title'],
               'subscribers':item['statistics']['subscriberCount'],
                'views':item['statistics']['viewCount'],
                'totalVideos':item['statistics']['videoCount'],
                'playlistId':item['contentDetails']['relatedPlaylists']['uploads']
               }
        
        all_data.append(data)

    return pd.DataFrame(all_data)

def get_video_ids(youtube, playlist_id):
    
    video_ids = []
    
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults = 50
    )
    response = request.execute()
    
    for item in response['items']:
        video_ids.append(item['contentDetails']['videoId'])
        
    next_page_token = response.get('nextPageToken')
    while next_page_token is not None:
        request = youtube.playlistItems().list(
                    part='contentDetails',
                    playlistId = playlist_id,
                    maxResults = 50,
                    pageToken = next_page_token)
        response = request.execute()

        for item in response['items']:
            video_ids.append(item['contentDetails']['videoId'])

        next_page_token = response.get('nextPageToken')
        
    return video_ids

def get_video_details(youtube, video_ids):

    all_video_info = []
    
    for i in range(0, len(video_ids), 50):
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=','.join(video_ids[i:i+50])
        )
        response = request.execute() 

        for video in response['items']:
            stats_to_keep = {'snippet': ['channelTitle', 'title', 'description', 'tags', 'publishedAt'],
                             'statistics': ['viewCount', 'likeCount', 'favouriteCount', 'commentCount'],
                             'contentDetails': ['duration', 'definition', 'caption']
                            }
            video_info = {}
            video_info['video_id'] = video['id']

            for k in stats_to_keep.keys():
                for v in stats_to_keep[k]:
                    try:
                        video_info[v] = video[k][v]
                    except:
                        video_info[v] = None

            all_video_info.append(video_info)
    
    return pd.DataFrame(all_video_info)

def process_data(video_df):

    video_df['publishedAt'] = video_df['publishedAt'].apply(lambda x: parser.parse(str(x))) 
    video_df['Publish Day'] = video_df['publishedAt'].apply(lambda x: x.strftime("%A")) 
    video_df['Duration in Seconds'] = video_df['duration'].apply(lambda x: isodate.parse_duration(x))
    video_df['Duration in Seconds'] = video_df['Duration in Seconds'].astype('timedelta64[s]')
    video_df['viewCount'] = video_df['viewCount'].astype('int64')
    video_df['likeCount'] = video_df['likeCount'].astype('int64')
    
    return video_df

def get_recent_vid_link(video_df):
    recent_vid = video_df['video_id'].values[0]
    link_recent_vid = f"https://www.youtube.com/watch?v={recent_vid}"
    return link_recent_vid

def get_most_viewed_vid_link(video_df):
    most_viewed_vid = video_df[['video_id','title', 'viewCount','publishedAt']].sort_values(by='viewCount', ascending=False).reset_index(drop=True).loc[0]
    vid_id_most_viewed_vid = most_viewed_vid[0]
    link_most_viewed_vid = f"https://www.youtube.com/watch?v={vid_id_most_viewed_vid}"
    return link_most_viewed_vid

def get_least_viewed_vid_link(video_df):
    least_viewed_vid = video_df[['video_id','title', 'viewCount','publishedAt']].sort_values(by='viewCount', ascending=True).reset_index(drop=True).loc[0]
    vid_id_least_viewed_vid = least_viewed_vid[0]
    link_least_viewed_vid = f"https://www.youtube.com/watch?v={vid_id_least_viewed_vid}"
    return link_least_viewed_vid

def top_five_videos_by_views(video_df):

    top_five_videos = video_df[['title', 'viewCount']]
    top_five_videos = top_five_videos.sort_values(by='viewCount', ascending=False)
    top_five_videos = top_five_videos.reset_index(drop=True).iloc[:5]
    top_five_videos_df = top_five_videos.rename(columns={top_five_videos.columns[0]: "Title", top_five_videos.columns[1]: "Views Count"})

    top_five_fig = px.bar(top_five_videos_df, x='Title', y='Views Count',
                hover_data=['Title', 'Views Count'], color_discrete_sequence=['indianred'],
                labels={'Title':'Views Count'}, height=600
                )

    return top_five_videos_df, top_five_fig

def top_five_videos_by_likes(video_df):

    top_five_videos = video_df[['title', 'likeCount']]
    top_five_videos = top_five_videos.sort_values(by='likeCount', ascending=False)
    top_five_videos = top_five_videos.reset_index(drop=True).iloc[:5]
    top_five_videos_df = top_five_videos.rename(columns={top_five_videos.columns[0]: "Title", top_five_videos.columns[1]: "Likes Count"})

    top_five_fig = px.bar(top_five_videos_df, x='Title', y='Likes Count',
                hover_data=['Title', 'Likes Count'], color_discrete_sequence=['indianred'],
                labels={'Title':'Likes Counts'}, height=600
                )

    return top_five_videos_df, top_five_fig

def create_sched_day_df(video_df):

    days = [ 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    from pandas.api.types import CategoricalDtype
    day = CategoricalDtype(categories=days, ordered=True)
    video_df['Publish Day'] = video_df['Publish Day'].astype(day)

    sched_day = video_df[['Publish Day']]
    frequency=collections.Counter(video_df['Publish Day']).values()
    sched_day  = sched_day .drop_duplicates(keep='first')
    sched_day.insert(1,'Count', frequency)
    sched_day = sched_day.sort_values(by=['Publish Day'], ascending=True).reset_index(drop=True)

    # sched_day.rename(columns = {'Publish Day':'Upload Day'}, inplace=True)
    
    sched_day_fig = px.bar(sched_day, x='Publish Day', y='Count',
             hover_data=['Publish Day', 'Count'], color_discrete_sequence=['indianred'],
             labels={'title':'videoCount'}, height=600
            )
    
    return sched_day, sched_day_fig

def count_seconds_per_vid(video_df):
    duration_videos_fig = px.histogram(video_df, x="Duration in Seconds",color_discrete_sequence=['indianred'])
    duration_videos_fig.update_layout(bargap=0.1)
    return duration_videos_fig

try:
    st.sidebar.header("Input Section")
    url = st.sidebar.text_input("Enter the URL of the Youtuber's Channel: ")
    channel_ids, channel_logo = get_channel_id_logo(url)
    st.image(channel_logo)
    channel_stats = get_channel_stats(youtube, channel_ids)
    playlist_id = channel_stats['playlistId'].values[0]
    video_ids = get_video_ids(youtube, playlist_id)
    video_dataF = pd.DataFrame(get_video_details(youtube, video_ids))
    # Data preprocessing
    video_df = process_data(video_dataF)
    # EXPLORATORY DATA ANALYSIS
    # Link to the Recent video
    link_recent_vid = get_recent_vid_link(video_df)
    # Link to the Most viewed video
    link_most_viewed_vid = get_most_viewed_vid_link(video_df)
    # Link to the least viewed video
    link_least_viewed_vid = get_least_viewed_vid_link(video_df)
    # Dataframe for the top 5 and Top 5 bar chart
    top_five_videos_by_views, top_five_fig_by_views = top_five_videos_by_views(video_df)
    top_five_videos_by_likes, top_five_fig_by_likes = top_five_videos_by_likes(video_df)
    # Get the DataFrame for upload per day and Sched day Bar chart
    sched_day_df, sched_day_fig = create_sched_day_df(video_df)
    # Average seconds per vid
    average_secs_per_vid = round(video_df['Duration in Seconds'].mean(),2)
    # Seconds per vid count
    duration_videos_fig = count_seconds_per_vid(video_df)
    #Video Dataframe for analysts
    youtuber_name = channel_stats['channelName'].values[0]
    st.subheader(f"{youtuber_name}")
    st.markdown("---")

    stat_c1, stat_c2, stat_c3 = st.columns(3)
    with stat_c1:
        st.metric("Total Subscribers",f"{n.numerize(int(channel_stats['subscribers'].values[0]))}")
    with stat_c2:
        st.metric("Number of Videos",f"{n.numerize(int(channel_stats['totalVideos'].values[0]))}")
    with stat_c3:
        st.metric("Total Views",f"{n.numerize(int(channel_stats['views'].values[0]))}")

    t1, t2, t3 = st.tabs(['Top 5 Videos', 'Upload Schedule', 'Videos Duration'])
    with t1:
        t1_col1, t1_col2 = st.columns(2)
        with t1_col1:
            st.subheader("Top 5 Videos by Views Count")
            st.plotly_chart(top_five_fig_by_views)
        with t1_col2:
            st.subheader("Top 5 Videos by Likes Count")
            st.plotly_chart(top_five_fig_by_likes)
    with t2:
        t2_col1, t2_col2 = st.columns(2)
        with t2_col1:
            st.subheader(f"When do {youtuber_name} usually uploads?")
            st.plotly_chart(sched_day_fig)
        with t2_col2:
            st.subheader('Interpretation')
            st.write(f"""_{youtuber_name}_ usually uploads on **{sched_day_df.sort_values(by='Count',ascending=False)['Publish Day'].values[0]}** 
            since the count of uploaded videos during that day is **{sched_day_df.sort_values(by='Count',ascending=False)['Count'].values[0]}** uploads.
            On the other hand, seeing that **{sched_day_df.sort_values(by='Count',ascending=True)['Publish Day'].values[0]}** has the lowest uploaded videos; 
            therefore _{youtuber_name}_ seldomly uploads during that day.""")
            st.subheader("Why scheduling of uploading a video is important?")
            st.caption('"YouTubers embracing a regular upload schedule will see a significant spike in traffic coming from the subscription feed. This results in improved watch time, as subscriber viewing sessions tend to last longer than non-subscribers."')
            st.caption("— ScaleLab")

            #st.caption(f"""Seeing that {sched_day_df.sort_values(by='Count',ascending=True)['Publish Day'].values[0]} has the lowest uploaded videos, therefore {youtuber_name} seldomly uploads during that day.""")
    with t3:
        t3_col1, t3_col2 = st.columns(2)
        with t3_col1:
            st.subheader(f"Average duration of {youtuber_name}'s videos")
            st.plotly_chart(duration_videos_fig)
        with t3_col2:
            st.subheader("Mean")
            st.subheader(f"{round(video_df['Duration in Seconds'].mean()/60,2)} minutes")
            st.caption(f"The exact mean duration of uploaded videos of {youtuber_name} in seconds is {round(video_df['Duration in Seconds'].mean(),2)} seconds.")
            st.subheader("What is the ideal YouTube video length?")
            st.caption('"Some creators have found success in longer-form content, but according to Statista’s report, the average YouTube video length is 11.7 minutes. We can rely on this report and add Social Media Examiner suggestion that claims: “In general videos between 7-15 minutes perform better."')
            st.caption("— Narakeet")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Most Recent Video")
        st.video(link_recent_vid)
    with col2:
        st.subheader("Most Viewed Video")
        st.video(link_most_viewed_vid)
    with col3:
        st.subheader("Least Viewed Video")
        st.video(link_least_viewed_vid)

    with st.expander("Data frame for future analysis"):
        st.subheader(f"{youtuber_name}'s Videos Dataframe")
        st.caption('This dataframe is used for creating visualizations and other features of this web-application. The data are extracted from the Youtube API v3.')
        st.dataframe(video_df)
        @st.cache
        def convert_df(df):
            return df.to_csv().encode('utf-8')

        csv = convert_df(video_df)

        st.download_button(
        "Download data as CSV",
        csv,
        f"{youtuber_name}_dataframe.csv",
        "text/csv",
        key='download-csv'
        )

except (KeyError, requests.exceptions.MissingSchema):
    with st.container():
        st.write("""
        YT St-Dash aims to aid users in analyzing YouTubers' activities by creating automated representations. This web application is deployed using the powerful Streamlit Python library. 

        **YT St-Dash** has the following features:
        - Rank videos by the number of views and count
        - Know the frequent day when the Youtuber uploads videos
        - Get the average duration length of  Youtuber's videos
        - Show the most liked, viewed, and recent videos
        - Prepare a downloadable CSV file of the Videos' Data frame """)
        st.markdown("---")
        st.header('How to use this web-application? ')
        st.subheader("[1] Go to Youtube and Search your desired Youtuber to analyze")
        st.image("instruction_one.jpg")
        st.subheader("[2] Click the profile picture of the Youtuber")
        st.image("instruction_two.jpg")
        st.subheader("[3] Copy (CTRL+C) the channel's URL")
        st.image("instruction_three.jpg")
        st.subheader("[4] Paste (CTRL+V) the URL to the Input Section and click ENTER")
        st.image("instruction_four.jpg")

st.markdown("---")






