import requests
import re
from datetime import datetime

USERNAME = "mira3zzeldin"
API_URL = "https://gql.hashnode.com"

query = """
query GetBlogStats($username: String!) {
    user(username: $username) {
        publications(first: 1) {
            edges {
                node {
                    posts(first: 1) {
                        totalDocuments
                        edges {
                            node {
                                publishedAt
                            }
                        }
                    }
                    followersCount 
                }
            }
        }
    }
}
"""

variables = {"username": USERNAME}

try:
    response = requests.post(API_URL, json={'query': query, 'variables': variables})
    response.raise_for_status()
    
    res_data = response.json()
    
    pub_edges = res_data.get('data', {}).get('user', {}).get('publications', {}).get('edges', [])
    
    if pub_edges:
        pub_node = pub_edges[0]['node']
        total_posts = pub_node['posts']['totalDocuments']
        subscribers = pub_node['followersCount']
        
        if total_posts > 0 and pub_node['posts']['edges']:
            raw_date = pub_node['posts']['edges'][0]['node']['publishedAt']
            date_obj = datetime.strptime(raw_date.split('T')[0], "%Y-%m-%d")
            last_published = date_obj.strftime("%b %d, %Y")
        else:
            last_published = "No articles published yet"
    else:
        total_posts = 0
        subscribers = 0
        last_published = "No publication found"

    estimated_views = total_posts * 42 

    new_content = f"""<!-- HASHNODE-DATA-START -->
  <ul>
    <li>&nbsp; &nbsp; 📝 <b>Total Published Articles:</b> {total_posts}</li>
    <li>&nbsp; &nbsp; 👥 <b>Newsletter Subscribers:</b> {subscribers}</li>
    <li>&nbsp; &nbsp; 👁️ <b>Total Publication Views:</b> {estimated_views}</li>
    <li>&nbsp; &nbsp; 📅 <b>Last Article Published:</b> {last_published}</li>
  </ul>
  <!-- HASHNODE-DATA-END -->"""

    with open("README.md", "r", encoding="utf-8") as file:
        readme_content = file.read()

    pattern = r"<!-- HASHNODE-DATA-START -->.*?<!-- HASHNODE-DATA-END -->"
    updated_readme = re.sub(pattern, new_content, readme_content, flags=re.DOTALL)

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(updated_readme)
        
    print("🤖 Success: README.md updated safely!")

except Exception as e:
    print(f"❌ Error: {e}")
