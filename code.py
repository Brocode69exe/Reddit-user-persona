import praw
from praw.models import Redditor
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import openai
import os
from typing import List, Dict, Any, Optional
import time

# Configuration - replace with your own API keys
REDDIT_CLIENT_ID = 'your_reddit_client_id'
REDDIT_CLIENT_SECRET = 'your_reddit_client_secret'
REDDIT_USER_AGENT = 'UserPersonaScraper/1.0 by yourusername'
OPENAI_API_KEY = 'your_openai_api_key'

# Initialize APIs
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

openai.api_key = OPENAI_API_KEY

def get_redditor_from_url(url: str) -> Optional[Redditor]:
    """Extract Redditor object from profile URL"""
    try:
        username = url.strip('/').split('/')[-1]
        if username.startswith('user/'):
            username = username[5:]
        return reddit.redditor(username)
    except Exception as e:
        print(f"Error getting Redditor: {e}")
        return None

def scrape_user_content(redditor: Redditor, limit: int = 100) -> Dict[str, List[Dict]]:
    """Scrape user's posts and comments"""
    content = {
        'posts': [],
        'comments': []
    }
    
    try:
        # Get posts
        for submission in redditor.submissions.new(limit=limit):
            content['posts'].append({
                'title': submission.title,
                'text': submission.selftext,
                'subreddit': submission.subreddit.display_name,
                'upvotes': submission.score,
                'url': submission.url,
                'created_utc': submission.created_utc,
                'is_original_content': submission.is_original_content
            })
    except Exception as e:
        print(f"Error scraping posts: {e}")
    
    try:
        # Get comments
        for comment in redditor.comments.new(limit=limit):
            content['comments'].append({
                'text': comment.body,
                'subreddit': comment.subreddit.display_name,
                'upvotes': comment.score,
                'url': f"https://reddit.com{comment.permalink}",
                'created_utc': comment.created_utc,
                'is_submitter': comment.is_submitter
            })
    except Exception as e:
        print(f"Error scraping comments: {e}")
    
    return content

def analyze_content_with_llm(content: Dict) -> Dict:
    """Use LLM to analyze content and generate persona"""
    # Prepare text for LLM
    text_samples = []
    
    for post in content['posts']:
        text_samples.append(f"POST in r/{post['subreddit']}: {post['title']}\n{post['text']}")
    
    for comment in content['comments']:
        text_samples.append(f"COMMENT in r/{comment['subreddit']}: {comment['text']}")
    
    full_text = "\n\n---\n\n".join(text_samples[:20]) 
    

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a skilled analyst that creates detailed user personas from social media content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error with LLM analysis: {e}")
        return None

def save_persona_to_file(username: str, persona: str, content: Dict):
  
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reddit_persona_{username}_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(persona)
        f.write("\n\n=== RAW DATA REFERENCES ===\n\n")
        
        f.write("=== POSTS ===\n")
        for i, post in enumerate(content['posts'], 1):
            f.write(f"{i}. {post['title']}\n")
            f.write(f"   Subreddit: r/{post['subreddit']}\n")
            f.write(f"   URL: {post['url']}\n")
            f.write(f"   Date: {datetime.fromtimestamp(post['created_utc'])}\n")
            f.write("-"*50 + "\n")
        
        f.write("\n=== COMMENTS ===\n")
        for i, comment in enumerate(content['comments'], 1):
            f.write(f"{i}. Comment in r/{comment['subreddit']}\n")
            f.write(f"   URL: {comment['url']}\n")
            f.write(f"   Date: {datetime.fromtimestamp(comment['created_utc'])}\n")
            f.write("-"*50 + "\n")
    
    print(f"Persona saved to {filename}")

def main():
    print("Reddit User Persona Generator")
    print("-----------------------------")
    
    profile_url = input("Enter Reddit profile URL: ").strip()
    
    redditor = get_redditor_from_url(profile_url)
    if not redditor:
        print("Could not access Reddit profile. Please check the URL and try again.")
        return
    
    print(f"\nScraping content for u/{redditor.name}...")
    content = scrape_user_content(redditor)
    
    if not content['posts'] and not content['comments']:
        print("No posts or comments found for this user.")
        return
    
    print("\nAnalyzing content and generating persona...")
    persona = analyze_content_with_llm(content)
    
    if persona:
        print("\n=== USER PERSONA ===\n")
        print(persona)
        save_persona_to_file(redditor.name, persona, content)
    else:
        print("Failed to generate persona.")

if __name__ == "__main__":
    main()