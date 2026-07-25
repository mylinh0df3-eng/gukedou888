from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs('data', exist_ok=True)
os.makedirs('uploads', exist_ok=True)

def load_data(filename):
    path = os.path.join('data', filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(filename, data):
    path = os.path.join('data', filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

SENSITIVE_WORDS = ['傻逼', '垃圾货', '骗子', '坑人']

def filter_sensitive(text):
    for word in SENSITIVE_WORDS:
        text = text.replace(word, '***')
    return text

def init_products():
    if not os.path.exists('data/products.json'):
        products = [
            {"id": "1", "name": "高级遮光窗帘", "category": "窗帘", "price": "¥168/米", "image": "https://via.placeholder.com/400x300/8b7355/fff?text=遮光窗帘", "description": "全遮光面料，隔热保温，多种颜色可选", "created_at": "2025-01-01"},
            {"id": "2", "name": "北欧风纱帘", "category": "窗帘", "price": "¥98/米", "image": "https://via.placeholder.com/400x300/a0845c/fff?text=北欧纱帘", "description": "透光不透影，营造温馨氛围", "created_at": "2025-01-05"},
            {"id": "3", "name": "纯棉四件套", "category": "家纺", "price": "¥399/套", "image": "https://via.placeholder.com/400x300/6b563f/fff?text=纯棉四件套", "description": "100%新疆长绒棉，亲肤透气", "created_at": "2025-01-10"},
            {"id": "4", "name": "客厅沙发垫", "category": "布艺", "price": "¥128/个", "image": "https://via.placeholder.com/400x300/8b7355/fff?text=沙发垫", "description": "防滑耐磨，可机洗，四季通用", "created_at": "2025-01-15"}
        ]
        save_data('products.json', products)

init_products()

@app.route('/')
def index():
    products = load_data('products.json')
    return render_template('index.html', products=products)

@app.route('/product/<product_id>')
def product_detail(product_id):
    products = load_data('products.json')
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return "产品不存在", 404
    reviews = load_data('reviews.json')
    product_reviews = [r for r in reviews if r['product_id'] == product_id and r['status'] == 'approved']
    if product_reviews:
        avg_rating = sum(r['rating'] for r in product_reviews) / len(product_reviews)
    else:
        avg_rating = 0
    return render_template('product.html', product=product, reviews=product_reviews, avg_rating=round(avg_rating, 1), review_count=len(product_reviews))

@app.route('/api/submit_review', methods=['POST'])
def submit_review():
    try:
        product_id = request.form.get('product_id')
        rating = int(request.form.get('rating', 5))
        content = request.form.get('content', '')
        reviewer_name = request.form.get('reviewer_name', '匿名用户')
        content = filter_sensitive(content)
        reviewer_name = filter_sensitive(reviewer_name)
        review = {
            "id": str(uuid.uuid4())[:12],
            "product_id": product_id,
            "rating": min(5, max(1, rating)),
            "content": content,
            "reviewer_name": reviewer_name,
            "proof_images": [],
            "status": "pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "replies": []
        }
        reviews = load_data('reviews.json')
        reviews.append(review)
        save_data('reviews.json', reviews)
        return jsonify({"success": True, "message": "评价已提交，等待审核"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/api/submit_reply', methods=['POST'])
def submit_reply():
    try:
        review_id = request.form.get('review_id')
        content = request.form.get('content', '')
        replier_name = request.form.get('replier_name', '商家')
        content = filter_sensitive(content)
        reviews = load_data('reviews.json')
        for review in reviews:
            if review['id'] == review_id:
                reply = {
                    "id": str(uuid.uuid4())[:8],
                    "content": content,
                    "replier_name": replier_name,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                review['replies'].append(reply)
                save_data('reviews.json', reviews)
                return jsonify({"success": True, "message": "回复成功"})
        return jsonify({"success": False, "message": "评价不存在"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@app.route('/admin')
def admin():
    reviews = load_data('reviews.json')
    products = load_data('products.json')
    return render_template('admin.html', reviews=reviews, products=products)

@app.route('/api/approve_review', methods=['POST'])
def approve_review():
    data = request.get_json()
    review_id = data.get('review_id')
    action = data.get('action')
    reviews = load_data('reviews.json')
    for review in reviews:
        if review['id'] == review_id:
            if action == 'approve':
                review['status'] = 'approved'
            elif action == 'reject':
                review['status'] = 'rejected'
            save_data('reviews.json', reviews)
            return jsonify({"success": True})
    return jsonify({"success": False, "message": "评价不存在"}), 404

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
