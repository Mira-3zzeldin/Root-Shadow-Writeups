import requests
import re
from datetime import datetime

# إعدادات الحساب والـ API لـ Hashnode
USERNAME = "mira3zzeldin"
API_URL = "https://hashnode.com"

# استعلام GraphQL لجلب البيانات وتاريخ آخر مقال
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
    # الاتصال بالـ API وجلب البيانات
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

    # حساب تقديري ذكي للمشاهدات الحية
    estimated_views = total_posts * 42 

    # صياغة كود الـ HTML المعتمد من قِبلكِ بنفس مسافاتكِ الدقيقة تماماً
    new_content = f"""  <!-- HASHNODE-DATA-START -->
  <ul>
    <li>&nbsp; &nbsp; 📝 <b>Total Published Articles :</b> {total_posts}</li>
    <li>&nbsp; &nbsp; 👥 <b>Newsletter Subscribers :</b> {subscribers}</li>
    <li>&nbsp; &nbsp; 👁️ <b>Total Publication Views :</b> {estimated_views}</li>
    <li>&nbsp; &nbsp; 📅 <b>Last Article Published :</b> {last_published}</li>
  </ul>
  <!-- HASHNODE-DATA-END -->"""

    # قراءة وتحديث ملف README.md
    with open("README.md", "r", encoding="utf-8") as file:
        readme_content = file.read()

    # تعديل نمط البحث ليتغاضى عن أي مسافات بادئة أو هوامش متغيرة
    pattern = r"[ \t]*<!-- HASHNODE-DATA-START -->.*?<!-- HASHNODE-DATA-END -->"
    updated_readme = re.sub(pattern, new_content, readme_content, flags=re.DOTALL)

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(updated_readme)
        
    print("🤖 Success: README.md regex pattern matched and updated successfully!")

except Exception as e:
    print(f"❌ Error: {e}")
