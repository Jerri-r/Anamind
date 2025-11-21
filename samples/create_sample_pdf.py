from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import textwrap

# 创建PDF样本文件
def create_sample_pdf():
    # 尝试使用中文字体，如果失败则使用英文
    try:
        pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.ttf'))
        font_name = 'SimHei'
    except:
        font_name = 'Helvetica'
    
    doc = SimpleDocTemplate("sample_beauty_sales.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 创建中文样式
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        spaceAfter=12
    )
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=16,
        spaceAfter=20
    )
    
    content = []
    
    # 标题
    content.append(Paragraph("美妆销售咨询记录", title_style))
    content.append(Spacer(1, 12))
    
    # 美妆咨询对话
    conversations = [
        "2024-03-10 09:30:15 美妆顾问：您好！欢迎来到美妆专柜，我是专业彩妆师小李，有什么可以帮助您的吗？",
        "2024-03-10 09:31:45 顾客：你好，我想买粉底，不知道什么适合我",
        "2024-03-10 09:32:30 美妆顾问：好的，请问您是什么肤质？平时化妆频率如何？",
        "2024-03-10 09:33:20 顾客：我是敏感肌，平时偶尔化妆",
        "2024-03-10 09:34:40 美妆顾问：那我推荐您试试我们的敏感肌专用粉底液，成分温和，不刺激",
        "2024-03-10 09:35:25 顾客：这个遮瑕效果怎么样？",
        "2024-03-10 09:36:35 美妆顾问：中等遮瑕，日常够用，如果有痘印可以配合遮瑕膏使用",
        "2024-03-10 09:37:15 顾客：多少钱？有试用装吗？",
        "2024-03-10 09:38:30 美妆顾问：268元，现在买送小样和美妆蛋",
        "2024-03-10 09:39:20 顾客：好的，那我试试",
        "",
        "2024-03-10 11:15:30 美妆顾问：您好！欢迎光临美妆专柜",
        "2024-03-10 11:16:10 顾客：你好，我想买眼线笔",
        "2024-03-10 11:17:25 美妆顾问：好的，请问您想要什么类型？液体还是胶笔？",
        "2024-03-10 11:18:15 顾客：我是新手，想要好上手的",
        "2024-03-10 11:19:30 美妆顾问：那我推荐您试试我们的眼线胶笔，很容易上手，不会出错",
        "2024-03-10 11:20:25 顾客：持久度怎么样？会晕染吗？",
        "2024-03-10 11:21:35 美妆顾问：持久度很好，防水的，日常8小时没问题",
        "2024-03-10 11:22:20 顾客：多少钱？",
        "2024-03-10 11:23:40 美妆顾问：88元，现在买送眼线卸妆液",
        "2024-03-10 11:24:15 顾客：好的，那我买一支",
        "",
        "2024-03-10 14:45:20 美妆顾问：您好！欢迎来到美妆专柜",
        "2024-03-10 14:46:05 顾客：你好，我想买腮红",
        "2024-03-10 14:47:30 美妆顾问：好的，请问您是什么肤色？想要什么效果？",
        "2024-03-10 14:48:20 顾客：我是白皮，想要自然一点的",
        "2024-03-10 14:49:40 美妆顾问：那我推荐您试试我们的粉色腮红，很显气色",
        "2024-03-10 14:50:25 顾客：会不会太显眼？",
        "2024-03-10 14:51:35 美妆顾问：不会的，很自然的粉色，淡淡的很可爱",
        "2024-03-10 14:52:15 顾客：多少钱？",
        "2024-03-10 14:53:30 美妆顾问：98元，买腮红送腮红刷",
        "2024-03-10 14:54:10 顾客：好的，那我买一个",
        "",
        "2024-03-10 16:20:45 美妆顾问：您好！欢迎光临美妆专柜",
        "2024-03-10 16:21:20 顾客：你好，我想买高光",
        "2024-03-10 16:22:35 美妆顾问：好的，请问您想要什么效果？自然还是闪亮？",
        "2024-03-10 16:23:25 顾客：日常用的，想要自然一点",
        "2024-03-10 16:24:40 美妆顾问：那我推荐您试试我们的珍珠高光，很细腻自然",
        "2024-03-10 16:25:20 顾客：飞粉严重吗？",
        "2024-03-10 16:26:35 美妆顾问：不飞粉，粉质很细腻，压得很实",
        "2024-03-10 16:27:15 顾客：多少钱？",
        "2024-03-10 16:28:30 美妆顾问：118元，现在有活动，买高光送高光刷",
        "2024-03-10 16:29:10 顾客：好的，那我买一个",
        "",
        "2024-03-10 18:15:30 美妆顾问：您好！欢迎来到美妆专柜",
        "2024-03-10 18:16:15 顾客：你好，我想买定妆粉",
        "2024-03-10 18:17:40 美妆顾问：好的，请问您是什么肤质？油皮还是干皮？",
        "2024-03-10 18:18:25 顾客：混合肌，T区比较油",
        "2024-03-10 18:19:35 美妆顾问：那我推荐您试试我们的控油定妆粉，专门为混合肌设计",
        "2024-03-10 18:20:20 顾客：会不会很干？",
        "2024-03-10 18:21:35 美妆顾问：不会的，含有保湿成分，控油的同时不拔干",
        "2024-03-10 18:22:15 顾客：多少钱？",
        "2024-03-10 18:23:30 美妆顾问：138元，买定妆粉送粉扑",
        "2024-03-10 18:24:10 顾客：好的，那我买一个",
    ]
    
    for line in conversations:
        if line.strip():
            # 处理长行，自动换行
            wrapped_lines = textwrap.wrap(line, width=80)
            for wrapped_line in wrapped_lines:
                content.append(Paragraph(wrapped_line, normal_style))
        else:
            content.append(Spacer(1, 6))
    
    # 构建PDF
    doc.build(content)
    print("PDF样本文件已创建：samples/sample_beauty_sales.pdf")

if __name__ == "__main__":
    create_sample_pdf()