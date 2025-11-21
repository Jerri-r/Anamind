from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3
import os
import json
from datetime import datetime, timedelta
import re
import PyPDF2
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pandas as pd
import numpy as np
import jieba
from wordcloud import WordCloud
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 数据库初始化和迁�?
def init_db():
    conn = sqlite3.connect('wechat_analysis.db')
    cursor = conn.cursor()
    
    # 创建上传记录�?
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS upload_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'processed'
        )
    ''')
    
    # 检查messages表是否存�?
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='messages'
    ''')
    
    messages_table_exists = cursor.fetchone()
    
    if messages_table_exists:
        # 检查是否有upload_id�?
        cursor.execute('PRAGMA table_info(messages)')
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'upload_id' not in column_names:
            # 添加upload_id�?
            cursor.execute('ALTER TABLE messages ADD COLUMN upload_id INTEGER')
            print("已添加upload_id列到messages�?)
        
        if 'sender_type' not in column_names:
            # 添加sender_type�?
            cursor.execute('ALTER TABLE messages ADD COLUMN sender_type TEXT DEFAULT "unknown"')
            print("已添加sender_type列到messages�?)
            
        if 'msg_type' not in column_names:
            # 添加msg_type�?
            cursor.execute('ALTER TABLE messages ADD COLUMN msg_type TEXT DEFAULT "text"')
            print("已添加msg_type列到messages�?)
    else:
        # 创建新的messages�?
        cursor.execute('''
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER,
                sender TEXT NOT NULL,
                sender_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                msg_type TEXT DEFAULT 'text',
                FOREIGN KEY (upload_id) REFERENCES upload_history (id)
            )
        ''')
        print("已创建新的messages�?)
    
    conn.commit()
    conn.close()

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'html', 'htm'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 文本解析函数
def parse_text_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return extract_messages(content)

# PDF解析函数
def parse_pdf_file(file_path):
    messages = []
    with open(file_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        content = ""
        for page in pdf_reader.pages:
"
        messages = extract_messages(content)
    return messages

# HTML解析函数
def parse_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text()
    return extract_messages(text_content)

# 消息提取和说话者识�?
def extract_messages(content):
    messages = []
    lines = content.strip().split('\n')
    
    # 常见的时间戳模式
    timestamp_patterns = [
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
        r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})',
        r'(\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2})',
        r'(\d{2}:\d{2})',
        r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})'
    ]
    
    # 说话者关键词
    operator_keywords = ['客服', '销�?, '店员', '顾问', 'assistant', 'sales', 'operator', 'staff', '彩妆顾问']
    customer_keywords = ['客户', '顾客', '用户', 'customer', 'user', 'buyer']
    
    # 提取客户名称的模�?
    customer_name_patterns = [
        r'(\w+小姐)�?,
        r'(\w+女士)�?,
        r'(\w+先生)�?,
        r'(\w+�?�?,
        r'(小\w+)�?,
        r'(老\w+)�?,
        r'(\w+经理)�?,
        r'(\w+主任)�?,
        r'(\w+)�?  # 通用模式，放在最�?
    ]
    
    current_message = {}
    current_customer = None  # 当前追踪的客�?
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 尝试匹配时间�?
        timestamp = None
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                timestamp = match.group(1)
                # 保存前一条消�?
                if current_message:
                    messages.append(current_message)
                # 开始新消息
                remaining_text = line.replace(timestamp, '').strip()
                current_message = {
                    'timestamp': timestamp,
                    'content': remaining_text,
                    'sender': 'Unknown',
                    'sender_type': 'unknown'
                }
                break
        
        if timestamp is not None and current_message:
            # 有时间戳的消息，需要识别说话�?
            content = current_message['content']
            
            # 检查是否是操作人员
            for keyword in operator_keywords:
                if keyword in content:
                    current_message['sender'] = content.split('�?)[0] if '�? in content else 'Operator'
                    current_message['sender_type'] = 'operator'
                    break
            else:
                # 检查是否是客户，尝试提取客户名�?
                for pattern in customer_name_patterns:
                    match = re.search(pattern, content)
                    if match:
                        customer_name = match.group(1)
                        current_message['sender'] = customer_name
                        current_message['sender_type'] = 'customer'
                        current_customer = customer_name  # 更新当前客户
                        break
                else:
                    # 如果没有匹配到特定模式，检查是否包含客户关键词
                    for keyword in customer_keywords:
                        if keyword in content:
                            current_message['sender'] = current_customer or 'Customer'
                            current_message['sender_type'] = 'customer'
                            break
        
        elif timestamp is None and current_message:
            # 如果没有时间戳但有当前消息，可能是多行消�?
            current_message['content'] += ' ' + line
        elif timestamp is None:
            # 检查是否是客户标记行（�?客户1: 李小�?�?
            customer_marker_match = re.match(r'客户\d+: (.+)', line)
            if customer_marker_match:
                current_customer = customer_marker_match.group(1)
            elif ':' in line and not any(keyword in line for keyword in operator_keywords):
                # 可能是客户说话但没有时间�?
                current_message = {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'content': line,
                    'sender': line.split('�?)[0] if '�? in line else current_customer or 'Customer',
                    'sender_type': 'customer'
                }
    
    # 保存最后一条消�?
    if current_message:
        messages.append(current_message)
    
    # 时间戳标准化
    for message in messages:
        try:
            parsed_time = date_parser.parse(message['timestamp'])
            message['timestamp'] = parsed_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            try:
                # 如果解析失败，尝试添加当前日�?
                if ':' in message['timestamp']:
                    time_part = message['timestamp']
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    full_timestamp = f"{current_date} {time_part}"
                    parsed_time = date_parser.parse(full_timestamp)
                    message['timestamp'] = parsed_time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                message['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return messages

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data_import')
def data_import():
    return render_template('data_import.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/table')
def table():
    return render_template('table.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    files = request.files.getlist('files')
    upload_results = []
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # 解析文件
            file_ext = filename.rsplit('.', 1)[1].lower()
            messages = []
            
            try:
                if file_ext == 'txt':
                    messages = parse_text_file(file_path)
                elif file_ext == 'pdf':
                    messages = parse_pdf_file(file_path)
                elif file_ext in ['html', 'htm']:
                    messages = parse_html_file(file_path)
                
                # 保存到数据库
                conn = sqlite3.connect('wechat_analysis.db')
                cursor = conn.cursor()
                
                # 插入上传记录
                cursor.execute('''
                    INSERT INTO upload_history (filename, file_type, upload_time, message_count)
                    VALUES (?, ?, ?, ?)
                ''', (filename, file_ext, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), len(messages)))
                
                upload_id = cursor.lastrowid
                
                # 插入消息记录
                for msg in messages:
                    cursor.execute('''
                        INSERT INTO messages (upload_id, sender, sender_type, content, timestamp, msg_type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (upload_id, msg['sender'], msg['sender_type'], msg['content'], msg['timestamp'], 'text'))
                
                conn.commit()
                conn.close()
                
                upload_results.append({
                    'filename': filename,
                    'status': 'success',
                    'message_count': len(messages)
                })
                
            except Exception as e:
                upload_results.append({
                    'filename': filename,
                    'status': 'error',
                    'error': str(e)
                })
    
    return jsonify({'results': upload_results})

@app.route('/upload_history')
def get_upload_history():
    conn = sqlite3.connect('wechat_analysis.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM upload_history ORDER BY upload_time DESC')
    history = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': row[0],
        'filename': row[1],
        'file_type': row[2],
        'upload_time': row[3],
        'message_count': row[4],
        'status': row[5]
    } for row in history])

@app.route('/delete_upload/<int:upload_id>', methods=['DELETE'])
def delete_upload(upload_id):
    conn = sqlite3.connect('wechat_analysis.db')
    cursor = conn.cursor()
    
    # 先删除相关的消息记录
    cursor.execute('DELETE FROM messages WHERE upload_id = ?', (upload_id,))
    # 再删除上传记�?
    cursor.execute('DELETE FROM upload_history WHERE id = ?', (upload_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/customer_overview')
def customer_overview():
    conn = sqlite3.connect('wechat_analysis.db')
    df = pd.read_sql_query('''
        SELECT DISTINCT 
            CASE 
                WHEN sender_type = 'customer' THEN sender
                ELSE 'Unknown Customer'
            END as customer_name,
            COUNT(DISTINCT DATE(timestamp)) as chat_days,
            COUNT(*) as total_messages,
            SUM(CASE 
                WHEN content LIKE '%转账%' OR content LIKE '%支付%' OR content LIKE '%购买%' OR content LIKE '%付款%' 
                THEN CAST(REPLACE(REPLACE(REPLACE(content, '�?, ''), '�?, ''), '¥', '') AS REAL)
                ELSE 0
            END) as transfer_amount
        FROM messages 
        WHERE sender_type = 'customer'
        GROUP BY customer_name
    ''', conn)
    conn.close()
    
    return jsonify(df.to_dict('records'))

@app.route('/api/chat_heatmap')
def chat_heatmap():
    customer_name = request.args.get('customer')
    
    conn = sqlite3.connect('wechat_analysis.db')
    
    # 构建查询条件
    where_clause = "WHERE sender_type = 'customer'"
    if customer_name and customer_name != 'all':
        where_clause += f" AND sender = '{customer_name}'"
    
    df = pd.read_sql_query(f'''
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as message_count
        FROM messages 
        {where_clause}
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', conn)
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        
        # 获取最新的月份数据
        latest_date = df['date'].max()
        year = latest_date.year
        month = latest_date.month
        
        # 创建当月的完整日�?
        import calendar
        cal = calendar.monthcalendar(year, month)
        
        # 创建消息计数字典
        message_counts = {}
        for _, row in df.iterrows():
            if row['date'].year == year and row['date'].month == month:
                message_counts[row['date'].day] = row['message_count']
        
        # 构建周数�?
        weeks_data = []
        for week in cal:
            week_data = []
            for day in week:
                if day == 0:  # 不属于当月的日期
                    week_data.append({'day': None, 'count': 0})
                else:
                    week_data.append({
                        'day': day, 
                        'count': message_counts.get(day, 0),
                        'date': f"{year}-{month:02d}-{day:02d}"
                    })
            weeks_data.append(week_data)
        
        return jsonify({
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month],
            'weeks': weeks_data
        })
    else:
        return jsonify({})

@app.route('/api/time_distribution')
def time_distribution():
    customer_name = request.args.get('customer')
    
    conn = sqlite3.connect('wechat_analysis.db')
    
    # 构建查询条件
    where_clause = "WHERE sender_type = 'customer'"
    if customer_name and customer_name != 'all':
        where_clause += f" AND sender = '{customer_name}'"
    
    df = pd.read_sql_query(f'''
        SELECT 
            CAST(strftime('%H', timestamp) AS INTEGER) as hour,
            COUNT(*) as message_count
        FROM messages 
        {where_clause}
        GROUP BY hour
        ORDER BY hour
    ''', conn)
    conn.close()
    
    # 填充0-23小时的完整数�?
    hours = list(range(24))
    df_full = pd.DataFrame({'hour': hours})
    df_result = df_full.merge(df, on='hour', how='left').fillna(0)
    
    return jsonify({
        'hours': df_result['hour'].tolist(),
        'message_counts': df_result['message_count'].astype(int).tolist()
    })

@app.route('/api/purchase_ratio')
def purchase_ratio():
    try:
        customer_name = request.args.get('customer')
        conn = sqlite3.connect('wechat_analysis.db')
        
        # 构建查询条件
        where_clause = "WHERE sender_type = 'customer'"
        if customer_name and customer_name != 'all':
            where_clause += f" AND sender = '{customer_name}'"
        
        # 按天分组，检查每天是否有转账记录
        df = pd.read_sql_query(f'''
            SELECT 
                DATE(timestamp) as chat_date,
                COUNT(*) as total_messages,
                MAX(CASE 
                    WHEN content LIKE '%转账%' OR content LIKE '%支付%' OR content LIKE '%付款%' OR 
                         content LIKE '%发红�?' OR content LIKE '%微信转账%' OR
                         content LIKE '%�?' OR content LIKE '%¥%' 
                    THEN 1
                    ELSE 0
                END) as has_transfer
            FROM messages 
            {where_clause}
            GROUP BY DATE(timestamp)
            ORDER BY chat_date
        ''', conn)
        conn.close()
        
        print(f"购买比例统计 - 原始数据行数: {len(df)}")
        
        if df.empty:
            print("没有聊天数据")
            return jsonify({'labels': ['暂无聊天数据'], 'values': [0]})
        
        # 分类统计：有转账的天�?vs 无转账的天数
        purchase_days = df[df['has_transfer'] > 0]['total_messages'].sum()
        non_purchase_days = df[df['has_transfer'] == 0]['total_messages'].sum()
        
        print(f"有转账天消息�? {purchase_days}, 无转账天消息�? {non_purchase_days}")
        
        # 如果没有任何有转账的�?
        if purchase_days == 0 and non_purchase_days > 0:
            return jsonify({
                'labels': ['Non-Purchase Days'],
                'values': [non_purchase_days]
            })
        
        # 如果只存在有转账的天
        if non_purchase_days == 0 and purchase_days > 0:
            return jsonify({
                'labels': ['Purchase Days'],
                'values': [purchase_days]
            })
        
        # 如果都没有数�?
        if purchase_days == 0 and non_purchase_days == 0:
            return jsonify({'labels': ['暂无数据'], 'values': [0]})
        
        return jsonify({
            'labels': ['Purchase Days', 'Non-Purchase Days'],
            'values': [purchase_days, non_purchase_days]
        })
        
    except Exception as e:
        print(f"购买比例API错误: {e}")
        return jsonify({'labels': ['加载失败'], 'values': [0]})

@app.route('/api/wordcloud')
def wordcloud():
    customer_name = request.args.get('customer')
    
    conn = sqlite3.connect('wechat_analysis.db')
    
    # 构建查询条件
    where_clause = "WHERE sender_type = 'customer'"
    if customer_name and customer_name != 'all':
        where_clause += f" AND sender = '{customer_name}'"
    
    df = pd.read_sql_query(f'''
        SELECT content FROM messages {where_clause}
    ''', conn)
    conn.close()
    
    if df.empty:
        return jsonify({'wordcloud': '', 'words': []})
    
    # 合并所有消息内�?
    all_text = ' '.join(df['content'].tolist())
    
    # 使用jieba分词，添加更多模�?
    jieba.initialize()  # 确保jieba初始�?
    words = jieba.lcut(all_text, cut_all=False)  # 精确模式
    
    # 扩展停用词列�?
    stop_words = {
        '�?, '�?, '�?, '�?, '�?, '�?, '�?, '�?, '�?, '�?, '�?, '�?, '一', '一�?, '�?, '�?, '�?, '�?, '�?, '�?, '�?, 
        '�?, '�?, '�?, '我们', '你们', '他们', '�?, '�?, '这个', '那个', '什�?, '怎么', '为什�?, '�?, '�?, '�?, '�?, 
        '�?, '呵呵', '谢谢', '你好', '再见', '好的', '可以', '是的', '不是', '没有', '还有', '然后', '或�?, '如果', '因为', 
        '所�?, '但是', '而且', '现在', '时�?, '地方', '东西', '问题', '办法', '知道', '觉得', '想要', '需�?, '可能', 
        '应该', '能够', '还是', '或�?, '或�?, '已经', '还是', '�?, '�?, '�?, '�?, '�?, '�?, '�?, '�?, '好的',
        '客服', '销�?, '店员', '顾客', '用户', '产品', '文件', '记录'
    }
    
    # 过滤停用词和短词，只保留中文词汇
    filtered_words = []
    for word in words:
        word = word.strip()
        # 检查是否为中文词汇
        if (len(word) >= 2 and 
            word not in stop_words and 
            word.isalpha() and 
            any('\u4e00' <= char <= '\u9fff' for char in word)):  # 包含中文字符
            filtered_words.append(word)
    
    # 统计词频，过滤低频词
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # 只保留出�?次以上的�?
    word_freq = {word: count for word, count in word_freq.items() if count >= 2}
    
    # 获取�?0个高频词
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # 生成词云�?
    if word_freq:
        # 尝试找到合适的中文字体
        font_path = None
        font_candidates = [
            'C:/Windows/Fonts/simhei.ttf',      # 黑体
            'C:/Windows/Fonts/msyh.ttc',        # 微软雅黑
            'C:/Windows/Fonts/simsun.ttc',      # 宋体
            'C:/Windows/Fonts/STXIHEI.TTF',    # 华文细黑
            'arial.ttf',                         # Arial 备用
        ]
        
        for font in font_candidates:
            if os.path.exists(font):
                font_path = font
                print(f"使用字体: {font}")
                break
        
        # 如果没有找到字体，返回简化版�?
        if not font_path:
            print("未找到中文字体，返回词频数据")
            return jsonify({
                'wordcloud': '',
                'words': [{'word': word, 'count': count} for word, count in top_words[:10]]
            })
        
        wc = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            font_path=font_path,
            max_words=30,
            min_font_size=12,
            max_font_size=50,
            relative_scaling=0.5,
            random_state=42,
            collocations=False,  # 不使用词语搭�?
            colormap='tab10'  # 使用彩色调色�?
        )
        
        try:
            wordcloud_img = wc.generate_from_frequencies(word_freq)
            
            # 转换为base64
            buffer = BytesIO()
            wordcloud_img.to_image().save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            print(f"词云图生成成功，�?个词: {list(word_freq.keys())[:5]}")
            
            return jsonify({
                'wordcloud': f'data:image/png;base64,{image_base64}',
                'words': [{'word': word, 'count': count} for word, count in top_words]
            })
        except Exception as e:
            print(f"词云图生成失�? {e}")
            # 返回词频数据作为备用
            return jsonify({
                'wordcloud': '',
                'words': [{'word': word, 'count': count} for word, count in top_words[:10]]
            })
    else:
        return jsonify({'wordcloud': '', 'words': []})

# 中国法定节假�?
def get_chinese_holidays(year):
    # 简化的中国法定节假日列�?
    holidays = {
        f"{year}-01-01": "元旦",
        f"{year}-02-10": "春节", f"{year}-02-11": "春节", f"{year}-02-12": "春节",
        f"{year}-04-05": "清明�?,
        f"{year}-05-01": "劳动�?,
        f"{year}-06-22": "端午�?,
        f"{year}-09-29": "中秋�?, f"{year}-09-30": "中秋�?,
        f"{year}-10-01": "国庆�?, f"{year}-10-02": "国庆�?, f"{year}-10-03": "国庆�?
    }
    return holidays

# 检查是否为周末
def is_weekend(date_str):
    date_obj = pd.to_datetime(date_str).date()
    return date_obj.weekday() >= 5  # 5=周六, 6=周日

# 检查是否为节假�?
def is_holiday_or_nearby(date_str, holidays, days_range=2):
    date_obj = pd.to_datetime(date_str).date()
    
    # 检查是否是节假�?
    if date_str in holidays:
        return True
    
    # 检查是否在节假日附近（前后几天�?
    for holiday_date in holidays.keys():
        holiday_obj = pd.to_datetime(holiday_date).date()
        if abs((date_obj - holiday_obj).days) <= days_range:
            return True
    
    return False

# 检查是否为促销日附�?
def is_promotion_nearby(date_str):
    date_obj = pd.to_datetime(date_str).date()
    # 检�?18附近
    june_18 = datetime(date_obj.year, 6, 18).date()
    if abs((date_obj - june_18).days) <= 3:  # 前后3�?
        return True
    
    # 检查双11附近
    nov_11 = datetime(date_obj.year, 11, 11).date()
    if abs((date_obj - nov_11).days) <= 3:  # 前后3�?
        return True
    
    return False

# 检查是否为节日附近
def is_festival_nearby(date_str):
    date_obj = pd.to_datetime(date_str).date()
    festivals = [
        (2, 14, "情人�?),    # 2�?4�?
        (3, 8, "三八�?),     # 3�?�?
        (5, 20, "520"),       # 5�?0�?
        (12, 25, "圣诞�?)     # 12�?5�?
    ]
    
    for month, day, name in festivals:
        festival_date = datetime(date_obj.year, month, day).date()
        if abs((date_obj - festival_date).days) <= 3:  # 前后3�?
            return True
    
    return False

@app.route('/api/customer_labels')
def customer_labels():
    try:
        conn = sqlite3.connect('wechat_analysis.db')
        
        # 获取所有客户消息数�?
        df = pd.read_sql_query('''
            SELECT 
                CASE 
                    WHEN sender_type = 'customer' THEN sender
                    ELSE 'Unknown Customer'
                END as customer_name,
                DATE(timestamp) as chat_date,
                timestamp,
                strftime('%H', timestamp) as hour,
                content,
                CASE 
                    WHEN content LIKE '%转账%' OR content LIKE '%支付%' OR content LIKE '%付款%' OR 
                         content LIKE '%发红�?' OR content LIKE '%微信转账%' OR
                         content LIKE '%�?' OR content LIKE '%¥%' 
                    THEN 1
                    ELSE 0
                END as has_transfer,
                CASE 
                    WHEN content LIKE '%好评%' OR content LIKE '%满意%' OR content LIKE '%不错%' OR
                         content LIKE '%很好%' OR content LIKE '%推荐%' OR content LIKE '%质量�?' OR
                         content LIKE '%服务�?' OR content LIKE '%再次购买%' OR content LIKE '%回购%'
                    THEN 1
                    ELSE 0
                END as has_positive_feedback,
                CASE 
                    WHEN content LIKE '%收到�?' OR content LIKE '%收到�?' OR content LIKE '%已经收到%' OR
                         content LIKE '%快递到�?' OR content LIKE '%已签�?' OR content LIKE '%到货�?'
                    THEN 1
                    ELSE 0
                END as has_received_goods
            FROM messages 
            WHERE sender_type = 'customer'
            ORDER BY chat_date, timestamp
        ''', conn)
        conn.close()
        
        if df.empty:
            return jsonify([])
        
        labels_result = []
        
        # 按客户分组分�?
        for customer, customer_data in df.groupby('customer_name'):
            # 1. Date Labels 分析
            date_labels = []
            
            # 计算每日消息频率
            daily_counts = customer_data.groupby('chat_date').size().reset_index(name='message_count')
            avg_count = daily_counts['message_count'].mean()
            
            # 检查促销�?
            promo_days = daily_counts[daily_counts['chat_date'].apply(is_promotion_nearby)]
            if not promo_days.empty and promo_days['message_count'].mean() > avg_count * 1.5:
                date_labels.append("Promotion-oriented")
            
            # 检查节假日
            holidays = get_chinese_holidays(customer_data['chat_date'].iloc[0][:4])
            holiday_days = daily_counts[daily_counts['chat_date'].apply(
                lambda x: is_holiday_or_nearby(x, holidays) or is_weekend(x)
            )]
            if not holiday_days.empty and holiday_days['message_count'].mean() > avg_count * 1.5:
                date_labels.append("Holiday-oriented")
            
            # 检查节�?
            festival_days = daily_counts[daily_counts['chat_date'].apply(is_festival_nearby)]
            if not festival_days.empty and festival_days['message_count'].mean() > avg_count * 1.5:
                date_labels.append("Festival-oriented")
            
            # 2. Time Labels 分析
            time_labels = []
            hour_counts = customer_data.groupby('hour').size()
            total_messages = len(customer_data)
            
            # 统计各时段消息数�?
            daytime_messages = hour_counts.loc[hour_counts.index.astype(int).between(8, 17)].sum()
            evening_messages = hour_counts.loc[hour_counts.index.astype(int).between(18, 23)].sum()
            early_morning_messages = hour_counts.loc[hour_counts.index.astype(int).between(0, 7)].sum()
            
            if daytime_messages / total_messages >= 0.5:
                time_labels.append("Daytime")
            if evening_messages / total_messages >= 0.5:
                time_labels.append("Evening")
            if early_morning_messages / total_messages >= 0.5:
                time_labels.append("Early Morning")
            
            # 3. Behaviour Labels 分析
            behaviour_labels = []
            
            # 计算购买会话数和总会话数
            chat_sessions = customer_data.groupby('chat_date').size().reset_index(name='session_messages')
            purchase_sessions = customer_data[customer_data['has_transfer'] == 1].groupby('chat_date').size().reset_index(name='purchase_sessions')
            
            total_sessions = len(chat_sessions)
            purchase_session_count = len(purchase_sessions)
            
            if total_sessions > 0:
                purchase_rate = purchase_session_count / total_sessions
                if purchase_rate < 1/20:  # 小于5%
                    behaviour_labels.append("Hesitant Buyers")
                elif purchase_rate >= 1/20:  # 大于等于5%
                    behaviour_labels.append("Quick Buyers")
            
            # 4. RFM 标签分析
            rfm_labels = calculate_rfm_labels(customer_data)
            
            # 5. Customer Lifecycle 标签分析
            lifecycle_labels = calculate_lifecycle_labels(customer_data)
            
            customer_labels = {
                'customer_name': customer,
                'basic_labels': {
                    'date_labels': date_labels,
                    'time_labels': time_labels,
                    'behaviour_labels': behaviour_labels
                },
                'analysis_labels': {
                    'rfm_labels': rfm_labels,
                    'lifecycle_labels': lifecycle_labels
                },
                'custom_labels': []  # 这里可以从数据库读取自定义标签，暂时为空
            }
            
            labels_result.append(customer_labels)
        
        return jsonify(labels_result)
        
    except Exception as e:
        print(f"客户标签API错误: {e}")
        return jsonify({'error': str(e)})

def calculate_rfm_labels(customer_data):
    """
    计算 RFM 标签
    R (Recency): 最近购买时�?
    F (Frequency): 购买次数
    M (Monetary): 消费金额
    """
    try:
        # 获取有购买记录的日期
        purchase_dates = customer_data[customer_data['has_transfer'] == 1]['chat_date'].unique()
        
        if len(purchase_dates) == 0:
            return ["No Purchase Data"]
        
        # 计算消费金额（简化处理，实际应该提取具体金额�?
        total_amount = len(purchase_dates) * 100  # 假设每次消费100�?
        
        # R - 最近购买时间（天数�?
        latest_purchase = pd.to_datetime(max(purchase_dates))
        current_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
        recency_days = (current_date - latest_purchase).days
        
        # F - 购买频率
        frequency = len(purchase_dates)
        
        # M - 消费金额
        monetary = total_amount
        
        # 根据业务规则定义高低阈�?
        r_threshold = 30  # 30天内为高
        f_threshold = 3   # 3次以上为�?
        m_threshold = 300 # 300元以上为�?
        
        # 判断高低
        r_level = "High" if recency_days <= r_threshold else "Low"
        f_level = "High" if frequency >= f_threshold else "Low"
        m_level = "High" if monetary >= m_threshold else "Low"
        
        # 根据RFM组合打标�?
        if r_level == "High" and f_level == "High" and m_level == "High":
            return ["Important Value Customers"]
        elif r_level == "High" and f_level == "Low" and m_level == "High":
            return ["Important Growth Customers"]
        elif r_level == "Low" and f_level == "High" and m_level == "High":
            return ["Important Retention Customers"]
        elif r_level == "Low" and f_level == "Low" and m_level == "High":
            return ["Important Win-Back Customers"]
        elif r_level == "High" and f_level == "High" and m_level == "Low":
            return ["General Value Customers"]
        elif r_level == "High" and f_level == "Low" and m_level == "Low":
            return ["General Growth Customers"]
        elif r_level == "Low" and f_level == "High" and m_level == "Low":
            return ["General Retention Customers"]
        else:  # r_level == "Low" and f_level == "Low" and m_level == "Low"
            return ["General Win-Back Customers"]
            
    except Exception as e:
        print(f"RFM标签计算错误: {e}")
        return ["RFM Calculation Error"]

def calculate_lifecycle_labels(customer_data):
    """
    计算 Customer Lifecycle 标签
    """
    try:
        # 获取所有聊天日�?
        chat_dates = customer_data['chat_date'].unique()
        purchase_dates = customer_data[customer_data['has_transfer'] == 1]['chat_date'].unique()
        
        # 统计反馈和收�?
        has_feedback = customer_data['has_positive_feedback'].sum() > 0
        has_received = customer_data['has_received_goods'].sum() > 0
        
        total_chat_days = len(chat_dates)
        total_purchases = len(purchase_dates)
        
        # Awareness Stage: 只有一次对�?
        if total_chat_days == 1:
            return ["Awareness Stage"]
        
        # Consideration Stage: 多次对话但没有下�?
        if total_chat_days > 1 and total_purchases == 0:
            return ["Consideration Stage"]
        
        # Purchase Stage: 第一次下�?
        if total_purchases == 1:
            # 检查是否已经收货但未评�?
            if has_received and not has_feedback:
                return ["Usage Stage"]
            else:
                return ["Purchase Stage"]
        
        # Loyalty Stage: 有正面反�?
        if has_feedback:
            return ["Loyalty Stage"]
        
        # Advocacy Stage: 第二次下�?
        if total_purchases >= 2:
            return ["Advocacy Stage"]
        
        # Churn Stage: 超过6个月没有聊天
        if len(chat_dates) > 0:
            latest_chat = pd.to_datetime(max(chat_dates))
            current_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
            days_since_last_chat = (current_date - latest_chat).days
            
            if days_since_last_chat > 180:  # 6个月
                return ["Churn Stage"]
        
        # 默认返回活跃状�?
        return ["Active Stage"]
        
    except Exception as e:
        print(f"Lifecycle标签计算错误: {e}")
        return ["Lifecycle Calculation Error"]

# 添加样本文件路由
@app.route('/samples/<filename>')
def serve_sample(filename):
    samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples')
    return send_from_directory(samples_dir, filename)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
