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

# 数据库初始化和迁移
def init_db():
    conn = sqlite3.connect('wechat_analysis.db')
    cursor = conn.cursor()
    
    # 创建上传记录表
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
    
    # 检查messages表是否存在
    cursor.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='messages'
    ''')
    
    messages_table_exists = cursor.fetchone()
    
    if messages_table_exists:
        # 检查是否有upload_id列
        cursor.execute('PRAGMA table_info(messages)')
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'upload_id' not in column_names:
            # 添加upload_id列
            cursor.execute('ALTER TABLE messages ADD COLUMN upload_id INTEGER')
            print("已添加upload_id列到messages表")
        
        if 'sender_type' not in column_names:
            # 添加sender_type列
            cursor.execute('ALTER TABLE messages ADD COLUMN sender_type TEXT DEFAULT "unknown"')
            print("已添加sender_type列到messages表")
            
        if 'msg_type' not in column_names:
            # 添加msg_type列
            cursor.execute('ALTER TABLE messages ADD COLUMN msg_type TEXT DEFAULT "text"')
            print("已添加msg_type列到messages表")
    else:
        # 创建新的messages表
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
        print("已创建新的messages表")
    
    # 创建自定义标签表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_custom_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            label_text TEXT NOT NULL,
            created_time TEXT NOT NULL,
            UNIQUE(customer_name, label_text)
        )
    ''')
    print("自定义标签表已就绪")
    
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
            content += page.extract_text() + "\n"
        messages = extract_messages(content)
    return messages

# HTML解析函数
def parse_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    text_content = soup.get_text()
    return extract_messages(text_content)

# 消息提取和说话者识别
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
    operator_keywords = ['客服', '销售', '店员', 'assistant', 'sales', 'operator', 'staff']
    customer_keywords = ['客户', '顾客', '用户', 'customer', 'user', 'buyer']
    
    current_message = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 尝试匹配时间戳
        timestamp = None
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                timestamp = match.group(1)
                # 保存前一条消息
                if current_message:
                    messages.append(current_message)
                # 开始新消息
                remaining_text = line.replace(timestamp, '').strip(':： ').strip()
                current_message = {
                    'timestamp': timestamp,
                    'content': remaining_text,
                    'sender': 'Unknown',
                    'sender_type': 'unknown'
                }
                break
        
        if timestamp is None and current_message:
            # 如果没有时间戳但有当前消息，追加内容
            current_message['content'] += ' ' + line
        elif timestamp is None:
            # 如果没有时间戳也没有当前消息，创建新消息
            current_message = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'content': line,
                'sender': 'Unknown',
                'sender_type': 'unknown'
            }
    
    # 保存最后一条消息
    if current_message:
        messages.append(current_message)
    
    # 说话者识别 - 改进的逻辑
    for message in messages:
        content = message['content']
        
        # 检查是否包含说话者标识 (格式: "人名：内容")
        if '：' in content or ':' in content:
            # 尝试提取说话者姓名
            parts = re.split(r'：|:', content, 1)
            if len(parts) >= 2:
                speaker = parts[0].strip()
                actual_content = parts[1].strip()
                
                # 更新消息内容
                message['content'] = actual_content
                
                # 根据说话者判断类型
                content_lower = speaker.lower()
                
                # 检查是否为操作员
                operator_keywords = ['客服', '销售', '店员', 'assistant', 'sales', 'operator', 'staff', '顾问', '专家']
                for keyword in operator_keywords:
                    if keyword in content_lower:
                        message['sender'] = speaker
                        message['sender_type'] = 'operator'
                        break
                else:
                    # 检查是否为客户关键词
                    customer_keywords = ['客户', '顾客', '用户', 'customer', 'user', 'buyer']
                    for keyword in customer_keywords:
                        if keyword in content_lower:
                            message['sender'] = speaker
                            message['sender_type'] = 'customer'
                            break
                    else:
                        # 默认规则：如果不是操作员，且内容包含购买意向等，认为是客户
                        purchase_indicators = ['我想', '我要', '请问', '多少钱', '价格', '买', '购买', '试试', '效果', '怎么样']
                        if any(indicator in actual_content for indicator in purchase_indicators):
                            message['sender'] = speaker
                            message['sender_type'] = 'customer'
                        else:
                            # 根据说话者格式判断 - 通常客户消息以姓名开头
                            if speaker and len(speaker) <= 4 and not any(char in speaker for char in '专员顾问专家客服销售'):
                                message['sender'] = speaker
                                message['sender_type'] = 'customer'
                            else:
                                message['sender'] = speaker
                                message['sender_type'] = 'unknown'
            else:
                # 如果分割失败，使用原有逻辑
                content_lower = content.lower()
                operator_keywords = ['客服', '销售', '店员', 'assistant', 'sales', 'operator', 'staff']
                for keyword in operator_keywords:
                    if keyword in content_lower:
                        message['sender'] = 'Operator'
                        message['sender_type'] = 'operator'
                        break
                else:
                    customer_keywords = ['客户', '顾客', '用户', 'customer', 'user', 'buyer']
                    for keyword in customer_keywords:
                        if keyword in content_lower:
                            message['sender'] = 'Customer'
                            message['sender_type'] = 'customer'
                            break
        else:
            # 没有冒号分隔的消息，使用原有逻辑
            content_lower = content.lower()
            operator_keywords = ['客服', '销售', '店员', 'assistant', 'sales', 'operator', 'staff']
            for keyword in operator_keywords:
                if keyword in content_lower:
                    message['sender'] = 'Operator'
                    message['sender_type'] = 'operator'
                    break
            else:
                customer_keywords = ['客户', '顾客', '用户', 'customer', 'user', 'buyer']
                for keyword in customer_keywords:
                    if keyword in content_lower:
                        message['sender'] = 'Customer'
                        message['sender_type'] = 'customer'
                        break
    
    # 时间戳标准化
    for message in messages:
        try:
            parsed_time = date_parser.parse(message['timestamp'])
            message['timestamp'] = parsed_time.strftime('%Y-%m-%d %H:%M:%S')
        except:
            try:
                # 如果解析失败，尝试添加当前日期
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
    # 再删除上传记录
    cursor.execute('DELETE FROM upload_history WHERE id = ?', (upload_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/api/customer_overview')
def customer_overview():
    conn = sqlite3.connect('wechat_analysis.db')
    # 先获取原始数据，然后用Python处理金额提取
    df_raw = pd.read_sql_query('''
        SELECT 
            CASE 
                WHEN sender_type = 'customer' THEN sender
                ELSE 'Unknown Customer'
            END as customer_name,
            content,
            DATE(timestamp) as chat_date
        FROM messages 
        WHERE sender_type = 'customer'
    ''', conn)
    
    # 提取转账金额的函数
    def extract_amount(content):
        import re
        # 匹配各种金额格式：1380元、￥68、¥100等
        patterns = [
            r'(\d+(?:\.\d+)?)\s*元',
            r'￥\s*(\d+(?:\.\d+)?)',
            r'¥\s*(\d+(?:\.\d+)?)',
            r'转账.*?(\d+(?:\.\d+)?)',
            r'支付.*?(\d+(?:\.\d+)?)',
            r'付款.*?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        return 0.0
    
    # 按客户分组计算
    result = []
    for customer, customer_data in df_raw.groupby('customer_name'):
        total_amount = sum(extract_amount(content) for content in customer_data['content'])
        chat_days = customer_data['chat_date'].nunique() if 'chat_date' in customer_data.columns else 1
        total_messages = len(customer_data)
        result.append({
            'customer_name': customer,
            'chat_days': int(chat_days),
            'total_messages': int(total_messages),
            'transfer_amount': float(total_amount)
        })
    
    df = pd.DataFrame(result)
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
        
        # 创建当月的完整日历
        import calendar
        cal = calendar.monthcalendar(year, month)
        
        # 创建消息计数字典
        message_counts = {}
        for _, row in df.iterrows():
            if row['date'].year == year and row['date'].month == month:
                message_counts[row['date'].day] = row['message_count']
        
        # 构建周数据
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
    
    # 填充0-23小时的完整数据
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
                         content LIKE '%发红包%' OR content LIKE '%微信转账%' OR
                         content LIKE '%￥%' OR content LIKE '%¥%' 
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
        
        # 分类统计：有转账的天数 vs 无转账的天数
        purchase_days = int(df[df['has_transfer'] > 0]['total_messages'].sum())
        non_purchase_days = int(df[df['has_transfer'] == 0]['total_messages'].sum())
        
        print(f"有转账天消息数: {purchase_days}, 无转账天消息数: {non_purchase_days}")
        
        # 如果没有任何有转账的天
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
        
        # 如果都没有数据
        if purchase_days == 0 and non_purchase_days == 0:
            return jsonify({'labels': ['暂无数据'], 'values': [0]})
        
        return jsonify({
            'labels': ['Purchase Days', 'Non-Purchase Days'],
            'values': [purchase_days, non_purchase_days]
        })
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"购买比例API错误: {e}")
        print(f"详细错误: {error_detail}")
        return jsonify({'labels': ['加载失败'], 'values': [0], 'error': str(e)})

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
    
    # 合并所有消息内容
    all_text = ' '.join(df['content'].tolist())
    
    # 使用jieba分词，添加更多模式
    jieba.initialize()  # 确保jieba初始化
    words = jieba.lcut(all_text, cut_all=False)  # 精确模式
    
    # 扩展停用词列表
    stop_words = {
        '的', '了', '我', '你', '是', '在', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', 
        '他', '她', '它', '我们', '你们', '他们', '这', '那', '这个', '那个', '什么', '怎么', '为什么', '吗', '呢', '啊', '吧', 
        '哈', '呵呵', '谢谢', '你好', '再见', '好的', '可以', '是的', '不是', '没有', '还有', '然后', '或者', '如果', '因为', 
        '所以', '但是', '而且', '现在', '时候', '地方', '东西', '问题', '办法', '知道', '觉得', '想要', '需要', '可能', 
        '应该', '能够', '还是', '或者', '或者', '已经', '还是', '给', '对', '吗', '吧', '呢', '啊', '哦', '嗯', '好的',
        '客服', '销售', '店员', '顾客', '用户', '产品', '文件', '记录'
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
    
    # 只保留出现2次以上的词
    word_freq = {word: count for word, count in word_freq.items() if count >= 2}
    
    # 获取前20个高频词
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # 生成词云图
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
        
        # 如果没有找到字体，返回简化版本
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
            collocations=False,  # 不使用词语搭配
            colormap='tab10'  # 使用彩色调色板
        )
        
        try:
            wordcloud_img = wc.generate_from_frequencies(word_freq)
            
            # 转换为base64
            buffer = BytesIO()
            wordcloud_img.to_image().save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            print(f"词云图生成成功，前5个词: {list(word_freq.keys())[:5]}")
            
            return jsonify({
                'wordcloud': f'data:image/png;base64,{image_base64}',
                'words': [{'word': word, 'count': count} for word, count in top_words]
            })
        except Exception as e:
            print(f"词云图生成失败: {e}")
            # 返回词频数据作为备用
            return jsonify({
                'wordcloud': '',
                'words': [{'word': word, 'count': count} for word, count in top_words[:10]]
            })
    else:
        return jsonify({'wordcloud': '', 'words': []})

# 中国法定节假日
def get_chinese_holidays(year):
    # 简化的中国法定节假日列表
    holidays = {
        f"{year}-01-01": "元旦",
        f"{year}-02-10": "春节", f"{year}-02-11": "春节", f"{year}-02-12": "春节",
        f"{year}-04-05": "清明节",
        f"{year}-05-01": "劳动节",
        f"{year}-06-22": "端午节",
        f"{year}-09-29": "中秋节", f"{year}-09-30": "中秋节",
        f"{year}-10-01": "国庆节", f"{year}-10-02": "国庆节", f"{year}-10-03": "国庆节"
    }
    return holidays

# 检查是否为周末
def is_weekend(date_str):
    date_obj = pd.to_datetime(date_str).date()
    return date_obj.weekday() >= 5  # 5=周六, 6=周日

# 检查是否为节假日
def is_holiday_or_nearby(date_str, holidays, days_range=2):
    date_obj = pd.to_datetime(date_str).date()
    
    # 检查是否是节假日
    if date_str in holidays:
        return True
    
    # 检查是否在节假日附近（前后几天）
    for holiday_date in holidays.keys():
        holiday_obj = pd.to_datetime(holiday_date).date()
        if abs((date_obj - holiday_obj).days) <= days_range:
            return True
    
    return False

# 检查是否为促销日附近
def is_promotion_nearby(date_str):
    date_obj = pd.to_datetime(date_str).date()
    # 检查618附近
    june_18 = datetime(date_obj.year, 6, 18).date()
    if abs((date_obj - june_18).days) <= 3:  # 前后3天
        return True
    
    # 检查双11附近
    nov_11 = datetime(date_obj.year, 11, 11).date()
    if abs((date_obj - nov_11).days) <= 3:  # 前后3天
        return True
    
    return False

# 检查是否为节日附近
def is_festival_nearby(date_str):
    date_obj = pd.to_datetime(date_str).date()
    festivals = [
        (2, 14, "情人节"),    # 2月14日
        (3, 8, "三八节"),     # 3月8日
        (5, 20, "520"),       # 5月20日
        (12, 25, "圣诞节")     # 12月25日
    ]
    
    for month, day, name in festivals:
        festival_date = datetime(date_obj.year, month, day).date()
        if abs((date_obj - festival_date).days) <= 3:  # 前后3天
            return True
    
    return False

@app.route('/api/customer_labels')
def customer_labels():
    try:
        conn = sqlite3.connect('wechat_analysis.db')
        
        # 获取所有客户消息数据
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
                         content LIKE '%发红包%' OR content LIKE '%微信转账%' OR
                         content LIKE '%￥%' OR content LIKE '%¥%' 
                    THEN 1
                    ELSE 0
                END as has_transfer,
                CASE 
                    WHEN content LIKE '%好评%' OR content LIKE '%满意%' OR content LIKE '%不错%' OR
                         content LIKE '%很好%' OR content LIKE '%推荐%' OR content LIKE '%质量好%' OR
                         content LIKE '%服务好%' OR content LIKE '%再次购买%' OR content LIKE '%回购%'
                    THEN 1
                    ELSE 0
                END as has_positive_feedback,
                CASE 
                    WHEN content LIKE '%收到货%' OR content LIKE '%收到了%' OR content LIKE '%已经收到%' OR
                         content LIKE '%快递到了%' OR content LIKE '%已签收%' OR content LIKE '%到货了%'
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
        
        # 按客户分组分析
        for customer, customer_data in df.groupby('customer_name'):
            # 1. Date Labels 分析
            date_labels = []
            
            # 计算每日消息频率
            daily_counts = customer_data.groupby('chat_date').size().reset_index(name='message_count')
            avg_count = daily_counts['message_count'].mean()
            
            # 检查促销日
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
            
            # 检查节日
            festival_days = daily_counts[daily_counts['chat_date'].apply(is_festival_nearby)]
            if not festival_days.empty and festival_days['message_count'].mean() > avg_count * 1.5:
                date_labels.append("Festival-oriented")
            
            # 2. Time Labels 分析
            time_labels = []
            # 确保小时是整数类型
            customer_data['hour'] = customer_data['hour'].astype(int)
            hour_counts = customer_data.groupby('hour').size()
            total_messages = len(customer_data)
            
            # 统计各时段消息数量
            daytime_messages = hour_counts[(hour_counts.index >= 8) & (hour_counts.index <= 17)].sum()
            evening_messages = hour_counts[(hour_counts.index >= 18) & (hour_counts.index <= 23)].sum()
            early_morning_messages = hour_counts[(hour_counts.index >= 0) & (hour_counts.index <= 7)].sum()
            
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
        import traceback
        error_detail = traceback.format_exc()
        print(f"客户标签API错误: {e}")
        print(f"详细错误: {error_detail}")
        return jsonify({'error': str(e), 'detail': error_detail})

def calculate_rfm_labels(customer_data):
    """
    计算 RFM 标签
    R (Recency): 最近购买时间
    F (Frequency): 购买次数
    M (Monetary): 消费金额
    """
    try:
        # 获取有购买记录的日期
        purchase_dates = customer_data[customer_data['has_transfer'] == 1]['chat_date'].unique()
        
        if len(purchase_dates) == 0:
            return ["No Purchase Data"]
        
        # 计算消费金额（简化处理，实际应该提取具体金额）
        total_amount = len(purchase_dates) * 100  # 假设每次消费100元
        
        # R - 最近购买时间（天数）
        latest_purchase = pd.to_datetime(max(purchase_dates))
        current_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
        recency_days = (current_date - latest_purchase).days
        
        # F - 购买频率
        frequency = len(purchase_dates)
        
        # M - 消费金额
        monetary = total_amount
        
        # 根据业务规则定义高低阈值
        r_threshold = 30  # 30天内为高
        f_threshold = 3   # 3次以上为高
        m_threshold = 300 # 300元以上为高
        
        # 判断高低
        r_level = "High" if recency_days <= r_threshold else "Low"
        f_level = "High" if frequency >= f_threshold else "Low"
        m_level = "High" if monetary >= m_threshold else "Low"
        
        # 根据RFM组合打标签
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
        # 获取所有聊天日期
        chat_dates = customer_data['chat_date'].unique()
        purchase_dates = customer_data[customer_data['has_transfer'] == 1]['chat_date'].unique()
        
        # 统计反馈和收货
        has_feedback = customer_data['has_positive_feedback'].sum() > 0
        has_received = customer_data['has_received_goods'].sum() > 0
        
        total_chat_days = len(chat_dates)
        total_purchases = len(purchase_dates)
        
        # Awareness Stage: 只有一次对话
        if total_chat_days == 1:
            return ["Awareness Stage"]
        
        # Consideration Stage: 多次对话但没有下单
        if total_chat_days > 1 and total_purchases == 0:
            return ["Consideration Stage"]
        
        # Purchase Stage: 第一次下单
        if total_purchases == 1:
            # 检查是否已经收货但未评价
            if has_received and not has_feedback:
                return ["Usage Stage"]
            else:
                return ["Purchase Stage"]
        
        # Loyalty Stage: 有正面反馈
        if has_feedback:
            return ["Loyalty Stage"]
        
        # Advocacy Stage: 第二次下单
        if total_purchases >= 2:
            return ["Advocacy Stage"]
        
        # Churn Stage: 超过6个月没有聊天
        if len(chat_dates) > 0:
            latest_chat = pd.to_datetime(max(chat_dates))
            current_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
            days_since_last_chat = (current_date - latest_chat).days
            
            if days_since_last_chat > 180:  # 6个月
                return ["Churn Stage"]
        
        # 默认返回活跃状态
        return ["Active Stage"]
        
    except Exception as e:
        print(f"Lifecycle标签计算错误: {e}")
        return ["Lifecycle Calculation Error"]

@app.route('/api/table_data')
def table_data():
    """
    获取表格数据，包含客户基本信息和所有标签
    """
    try:
        conn = sqlite3.connect('wechat_analysis.db')
        
        # 获取客户概览数据
        df_customers = pd.read_sql_query('''
            SELECT DISTINCT 
                CASE 
                    WHEN sender_type = 'customer' THEN sender
                    ELSE 'Unknown Customer'
                END as customer_name,
                COUNT(DISTINCT DATE(timestamp)) as chat_days,
                COUNT(*) as total_messages
            FROM messages 
            WHERE sender_type = 'customer'
            GROUP BY customer_name
        ''', conn)
        
        # 获取所有客户标签数据
        df_labels = pd.read_sql_query('''
            SELECT 
                CASE 
                    WHEN sender_type = 'customer' THEN sender
                    ELSE 'Unknown Customer'
                END as customer_name,
                content,
                DATE(timestamp) as chat_date,
                strftime('%H', timestamp) as hour,
                CASE 
                    WHEN content LIKE '%转账%' OR content LIKE '%支付%' OR content LIKE '%付款%' OR 
                         content LIKE '%发红包%' OR content LIKE '%微信转账%' OR
                         content LIKE '%￥%' OR content LIKE '%¥%' 
                    THEN 1
                    ELSE 0
                END as has_transfer,
                CASE 
                    WHEN content LIKE '%好评%' OR content LIKE '%满意%' OR content LIKE '%不错%' OR
                         content LIKE '%很好%' OR content LIKE '%推荐%' OR content LIKE '%质量好%' OR
                         content LIKE '%服务好%' OR content LIKE '%再次购买%' OR content LIKE '%回购%'
                    THEN 1
                    ELSE 0
                END as has_positive_feedback,
                CASE 
                    WHEN content LIKE '%收到货%' OR content LIKE '%收到了%' OR content LIKE '%已经收到%' OR
                         content LIKE '%快递到了%' OR content LIKE '%已签收%' OR content LIKE '%到货了%'
                    THEN 1
                    ELSE 0
                END as has_received_goods
            FROM messages 
            WHERE sender_type = 'customer'
            ORDER BY chat_date, timestamp
        ''', conn)
        
        if df_customers.empty:
            return jsonify([])
        
        # 为每个客户提取转账金额和自定义标签
        result = []
        for _, customer_row in df_customers.iterrows():
            customer_name = customer_row['customer_name']
            customer_data = df_labels[df_labels['customer_name'] == customer_name]
            
            # 提取转账金额
            total_amount = 0.0
            if not customer_data.empty:
                for content in customer_data['content']:
                    # 使用正则表达式提取金额
                    import re
                    patterns = [
                        r'(\d+(?:\.\d+)?)\s*元',
                        r'￥\s*(\d+(?:\.\d+)?)',
                        r'¥\s*(\d+(?:\.\d+)?)',
                        r'转账.*?(\d+(?:\.\d+)?)',
                        r'支付.*?(\d+(?:\.\d+)?)',
                        r'付款.*?(\d+(?:\.\d+)?)'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, content)
                        if match:
                            try:
                                total_amount += float(match.group(1))
                            except:
                                continue
            
            # 获取自定义标签
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT label_text 
                    FROM customer_custom_labels 
                    WHERE customer_name = ?
                    ORDER BY created_time DESC
                ''', (customer_name,))
                
                custom_labels = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                print(f"获取自定义标签失败: {e}")
                custom_labels = []
            
            # 计算客户标签
            basic_labels = []
            rfm_labels = calculate_rfm_labels(customer_data)
            lifecycle_labels = calculate_lifecycle_labels(customer_data)
            
            # 获取基础标签（Date Labels, Time Labels, Behaviour Labels）
            if not customer_data.empty:
                # Date Labels
                daily_counts = customer_data.groupby('chat_date').size().reset_index(name='message_count')
                if not daily_counts.empty:
                    avg_count = daily_counts['message_count'].mean()
                    
                    promo_days = daily_counts[daily_counts['chat_date'].apply(is_promotion_nearby)]
                    if not promo_days.empty and promo_days['message_count'].mean() > avg_count * 1.5:
                        basic_labels.append("Promotion-oriented")
                    
                    holidays = get_chinese_holidays(str(customer_data['chat_date'].iloc[0])[:4])
                    holiday_days = daily_counts[daily_counts['chat_date'].apply(
                        lambda x: is_holiday_or_nearby(x, holidays) or is_weekend(x)
                    )]
                    if not holiday_days.empty and holiday_days['message_count'].mean() > avg_count * 1.5:
                        basic_labels.append("Holiday-oriented")
                    
                    festival_days = daily_counts[daily_counts['chat_date'].apply(is_festival_nearby)]
                    if not festival_days.empty and festival_days['message_count'].mean() > avg_count * 1.5:
                        basic_labels.append("Festival-oriented")
                
                # Time Labels
                hour_counts = customer_data.groupby('hour').size()
                if not hour_counts.empty:
                    total_messages = len(customer_data)
                    hour_counts.index = hour_counts.index.astype(int)
                    
                    daytime_messages = hour_counts.loc[(hour_counts.index >= 8) & (hour_counts.index <= 17)].sum()
                    evening_messages = hour_counts.loc[(hour_counts.index >= 18) & (hour_counts.index <= 23)].sum()
                    early_morning_messages = hour_counts.loc[(hour_counts.index >= 0) & (hour_counts.index <= 7)].sum()
                    
                    if daytime_messages / total_messages >= 0.5:
                        basic_labels.append("Daytime")
                    if evening_messages / total_messages >= 0.5:
                        basic_labels.append("Evening")
                    if early_morning_messages / total_messages >= 0.5:
                        basic_labels.append("Early Morning")
                
                # Behaviour Labels
                chat_sessions = customer_data.groupby('chat_date').size().reset_index(name='session_messages')
                purchase_sessions = customer_data[customer_data['has_transfer'] == 1].groupby('chat_date').size().reset_index(name='purchase_sessions')
                
                total_sessions = len(chat_sessions)
                purchase_session_count = len(purchase_sessions)
                
                if total_sessions > 0:
                    purchase_rate = purchase_session_count / total_sessions
                    if purchase_rate < 1/20:
                        basic_labels.append("Hesitant Buyers")
                    elif purchase_rate >= 1/20:
                        basic_labels.append("Quick Buyers")
            
            # 构建结果
            result.append({
                'customer_name': customer_name,
                'chat_days': int(customer_row['chat_days']),
                'total_messages': int(customer_row['total_messages']),
                'transfer_amount': float(total_amount),
                'basic_labels': basic_labels,
                'rfm_labels': rfm_labels,
                'lifecycle_labels': lifecycle_labels,
                'custom_labels': custom_labels
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"表格数据API错误: {e}")
        print(f"详细错误: {error_detail}")
        return jsonify({'error': str(e)})

@app.route('/api/custom_labels/<customer_name>', methods=['GET', 'POST', 'DELETE'])
def custom_labels(customer_name):
    """
    管理客户的自定义标签
    GET: 获取客户的所有自定义标签
    POST: 添加新的自定义标签
    DELETE: 删除指定的自定义标签
    """
    try:
        conn = sqlite3.connect('wechat_analysis.db')
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # 获取客户的所有自定义标签
            cursor.execute('''
                SELECT label_text, created_time 
                FROM customer_custom_labels 
                WHERE customer_name = ? 
                ORDER BY created_time DESC
            ''', (customer_name,))
            
            labels = cursor.fetchall()
            conn.close()
            
            return jsonify([{
                'label': label[0],
                'created_time': label[1]
            } for label in labels])
        
        elif request.method == 'POST':
            # 添加新的自定义标签
            data = request.get_json()
            label_text = data.get('label', '').strip()
            
            if not label_text:
                return jsonify({'error': '标签内容不能为空'}), 400
            
            cursor.execute('''
                INSERT INTO customer_custom_labels (customer_name, label_text, created_time)
                VALUES (?, ?, ?)
            ''', (customer_name, label_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'label': label_text})
        
        elif request.method == 'DELETE':
            # 删除自定义标签
            data = request.get_json()
            label_text = data.get('label', '').strip()
            
            if not label_text:
                return jsonify({'error': '标签内容不能为空'}), 400
            
            cursor.execute('''
                DELETE FROM customer_custom_labels 
                WHERE customer_name = ? AND label_text = ?
            ''', (customer_name, label_text))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'label': label_text})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 添加样本文件路由
@app.route('/samples/<filename>')
def serve_sample(filename):
    samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples')
    return send_from_directory(samples_dir, filename)

if __name__ == '__main__':
    init_db()
    # 生产环境配置
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)