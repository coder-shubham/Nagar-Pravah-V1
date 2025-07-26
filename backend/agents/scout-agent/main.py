# Scout Agent - main.py
import os
import json
import requests
import tweepy
import feedparser
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from google.cloud import firestore
from utils import NagarPravahUtils

app = Flask(__name__)

class ScoutAgent:
    """Agent responsible for fetching data from external sources"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.utils = NagarPravahUtils(os.getenv('GEMINI_API_KEY'))
        
        # Initialize API clients
        self.setup_twitter_client()
        self.setup_data_sources()
    
    def setup_twitter_client(self):
        """Initialize Twitter API client"""
        try:
            auth = tweepy.OAuthHandler(
                os.getenv('TWITTER_CONSUMER_KEY'),
                os.getenv('TWITTER_CONSUMER_SECRET')
            )
            auth.set_access_token(
                os.getenv('TWITTER_ACCESS_TOKEN'),
                os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            self.twitter_api = tweepy.API(auth)
        except Exception as e:
            print(f"Error setting up Twitter client: {e}")
            self.twitter_api = None
    
    def setup_data_sources(self):
        """Define all data sources to monitor"""
        self.data_sources = {
            'twitter_accounts': [
                '@blrcitytraffic',
                '@BangaloreMirror',
                '@TOIBengaluru',
                '@DeccanHerald'
            ],
            'rss_feeds': [
                'https://timesofindia.indiatimes.com/city/bengaluru/rssfeeds/2950623.cms',
                'https://www.deccanherald.com/rss/bengaluru.xml',
                'https://bangaloremirror.indiatimes.com/rss.cms'
            ],
            'event_apis': [
                # Add event page APIs here
            ]
        }
    
    def fetch_twitter_data(self) -> list:
        """Fetch recent tweets from configured accounts"""
        tweets_data = []
        
        if not self.twitter_api:
            return tweets_data
        
        for account in self.data_sources['twitter_accounts']:
            try:
                # Get recent tweets (last 5 minutes worth)
                tweets = tweepy.Cursor(
                    self.twitter_api.user_timeline,
                    screen_name=account,
                    include_rts=False,
                    exclude_replies=True,
                    tweet_mode='extended'
                ).items(10)  # Get last 10 tweets to filter by time
                
                for tweet in tweets:
                    # Check if tweet is from last 10 minutes
                    tweet_time = tweet.created_at.replace(tzinfo=timezone.utc)
                    time_diff = datetime.now(timezone.utc) - tweet_time
                    
                    if time_diff.total_seconds() <= 600:  # 10 minutes
                        tweet_data = {
                            'source': 'twitter',
                            'source_id': str(tweet.id),
                            'content': tweet.full_text,
                            'raw_metadata': {
                                'user_handle': tweet.user.screen_name,
                                'user_name': tweet.user.name,
                                'retweet_count': tweet.retweet_count,
                                'favorite_count': tweet.favorite_count,
                                'created_at': tweet.created_at.isoformat(),
                                'tweet_url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"
                            },
                            'fetched_at': firestore.SERVER_TIMESTAMP
                        }
                        tweets_data.append(tweet_data)
                        
            except Exception as e:
                print(f"Error fetching tweets from {account}: {e}")
                continue
        
        return tweets_data
    
    def fetch_rss_data(self) -> list:
        """Fetch recent articles from RSS feeds"""
        rss_data = []
        
        for feed_url in self.data_sources['rss_feeds']:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # Get latest 5 entries
                    # Check if entry is recent (last 2 hours)
                    if hasattr(entry, 'published_parsed'):
                        entry_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        time_diff = datetime.now(timezone.utc) - entry_time
                        
                        if time_diff.total_seconds() <= 7200:  # 2 hours
                            article_data = {
                                'source': 'news_rss',
                                'source_id': entry.link,
                                'content': f"{entry.title}. {entry.summary}",
                                'raw_metadata': {
                                    'title': entry.title,
                                    'link': entry.link,
                                    'published': entry.published if hasattr(entry, 'published') else '',
                                    'author': entry.author if hasattr(entry, 'author') else '',
                                    'feed_source': feed_url
                                },
                                'fetched_at': firestore.SERVER_TIMESTAMP
                            }
                            rss_data.append(article_data)
                            
            except Exception as e:
                print(f"Error fetching RSS from {feed_url}: {e}")
                continue
        
        return rss_data
    
    def fetch_user_reports(self) -> list:
        """Simulate fetching user reports - integrate with actual user report system"""
        # This would integrate with your user report collection system
        # For now, returning empty list as placeholder
        return []
    
    def store_scouted_data(self, data_items: list) -> bool:
        """Store fetched data in Firestore scouted-data collection"""
        try:
            batch = self.db.batch()
            collection_ref = self.db.collection('scouted-data')
            
            for item in data_items:
                doc_ref = collection_ref.document()  # Auto-generate ID
                batch.set(doc_ref, item)
            
            batch.commit()
            print(f"Successfully stored {len(data_items)} items")
            return True
            
        except Exception as e:
            print(f"Error storing data: {e}")
            return False
    
    def run_scout_cycle(self):
        """Execute one complete scout cycle"""
        print("Starting scout cycle...")
        
        all_data = []
        
        # Fetch from all sources
        twitter_data = self.fetch_twitter_data()
        rss_data = self.fetch_rss_data()
        user_reports = self.fetch_user_reports()
        
        all_data.extend(twitter_data)
        all_data.extend(rss_data)
        all_data.extend(user_reports)
        
        print(f"Fetched {len(all_data)} items from all sources")
        
        # Store in Firestore
        if all_data:
            success = self.store_scouted_data(all_data)
            return {"status": "success", "items_processed": len(all_data)}
        else:
            return {"status": "success", "items_processed": 0, "message": "No new data found"}


# Flask routes for Cloud Run
@app.route('/', methods=['POST', 'GET'])
def main():
    """Main entry point for Cloud Scheduler trigger"""
    try:
        scout = ScoutAgent()
        result = scout.run_scout_cycle()
        return jsonify(result), 200
    except Exception as e:
        print(f"Error in scout agent: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)