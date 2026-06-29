'''各种自定义函数，都写在这里，直接调用即可'''
#############################################################################
import pytds as sql  # pip install python-tds -i https://pypi.tuna.tsinghua.edu.cn/simple，可能得X.10版本中才能使X
import pytds
import pandas as pd
import requests
import hashlib
# import time
import json
import re
from datetime import date,time,datetime,timedelta
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options

#########################################################################
def connect_tc_db():
    return sql.connect(
        server=os.environ.get("TC_DB_SERVER", "223.78.73.100"),
        user=os.environ.get("TC_DB_USER", "sa"),
        password=os.environ.get("TC_DB_PASSWORD", ""),
        database=os.environ.get("TC_DB_DATABASE", "TC"),
    )

#########################################################################
def sf_db(SQL, params=None):
    # 开发日期：2025-05-05
    # 功能：实现对数据库的select操作。sf=select from
    # 参数说明X
    #     SQL：SQL语句
    if isinstance(params, bool):
        params = None
    con = connect_tc_db()
    try:
        cursor = con.cursor()
        cursor.execute(SQL, params or ())
        rs = cursor.fetchall()                      # rs是个列表，里面每个元素是一个元组，形如：[('A', 'A1'), ('B', 'B1')]

        if not rs or len(rs) == 0:                  # 修复：检查结果集是否为空
            return []

        if len(rs)==1 and len(rs[0]) == 1:          # 返回单个值，必须判断两个条件
            return rs[0][0]

        if len(rs[0]) == 1:                         # 如果返回的结果只有一列，就直接转化为列表，避免列表里面套元组
            myList = []
            for e in rs:
                myList.append(e[0])
            return myList
        else:
            return rs                               # 直接返回列表
    finally:
        con.close()


#########################################################################
def dui_db(SQL, params=None, show_result=False):
    # 开发日期：2025-05-05
    # 功能：实现对数据库的update、delete、insert操作。dui=delete、update、insert
    # 参数说明X
    #         SQL：SQL语句
    # show_result：是否显示影响了多少条数X

    if isinstance(params, bool):
        show_result = params
        params = None
    conn = connect_tc_db()
    try:
        cursor = conn.cursor()                  # 创建游标
        cursor.execute(SQL, params or ())

        if show_result==True:
            print(f"更新了 {cursor.rowcount} 条记录")
        if not conn.autocommit:
            conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


#########################################################################
def dui_db_many(sql_params_list):
    # 功能：在同一个事务中执行多条insert/update/delete语句
    conn = connect_tc_db()
    try:
        cursor = conn.cursor()
        rowcounts = []
        for SQL, params in sql_params_list:
            cursor.execute(SQL, params or ())
            rowcounts.append(cursor.rowcount)
        if not conn.autocommit:
            conn.commit()
        return rowcounts
    except Exception:
        if not conn.autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()


#########################################################################
def get_cname():
    # 获取本机计算机名
    import socket
    return socket.getfqdn(socket.gethostname())

#########################################################################
def get_uname():
    """开发日期：2025-09-15
       功能：获取当前用户名
    """
    s=f"SELECT UName FROM ComputerName WHERE CName='{get_cname()}'"
    return sf_db(s)

#########################################################################
def text_to_file(s,fullpath):
    # 开发日期：2025-04-14
    # 功能：将指定的字符串写入到指定的txt文件X
    f=open(fullpath,'a', encoding='utf-8')                        # 打开文件以便写入，a:追加append，w：写入write
    print(s,file=f)
    f.close()

#########################################################################
def append_to_file(content,file_path):
    # 功能：将字符串追加写入到指定的文本文件中（不覆盖原有内容X
    # 参数说明X
    #   content: 要追加的字符X
    # file_path: 完整的目标文件路X
    with open(file_path, mode='a', encoding='utf-8') as file:
        file.write(content)

#########################################################################
def baidu_translate(text: str) -> str:
    '''英文翻译中文'''
    # ========== 配置 ==========
    APP_ID = os.environ.get("BAIDU_TRANSLATE_APP_ID", "")
    SECRET_KEY = os.environ.get("BAIDU_TRANSLATE_SECRET_KEY", "")
    FROM_LANG = 'en'
    TO_LANG = 'zh'
    API_URL = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
    if pd.isna(text) or str(text).strip() == '':
        return ''
    if not APP_ID or not SECRET_KEY:
        return '请先配置百度翻译密钥'

    text = str(text).strip()
    salt = str(int(time.time() * 1000))  # 毫秒Xsalt
    sign_str = APP_ID + text + salt + SECRET_KEY
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()

    params = {'q': text,
           'from': FROM_LANG,
             'to': TO_LANG,
          'appid': APP_ID,
           'salt': salt,
           'sign': sign}

    try:
        resp = requests.get(API_URL, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data['trans_result'][0]['dst']
    except Exception as e:
        print(f'翻译失败：{text} -> {e}')
        return '翻译失败'

#########################################################################
def get_user_accessible_skus(lei_xing=1):
    # 获取当前电脑用户可以访问的SKU列表
    # 返回：可访问的SKU列表
    computer_name = get_cname()
    sql_query = f"""
    SELECT distinct ZhuSKU 
      FROM ZiDian 
     WHERE Dian in (SELECT Dian 
                      FROM DianQuanXian 
                     WHERE LeiXing={lei_xing} and YunYing=(SELECT UName
                                                    FROM ComputerName
                                                   WHERE cname='{computer_name}'))
    """
    try:
        accessible_skus = sf_db(sql_query)
        return accessible_skus
    except Exception as e:
        print(f"获取用户权限失败：{e}")
        return []

#########################################################################
def sku_yunxu(sku,lei_xing=1):
    # 功能检查当前用户是否有权限访问指定的SKU
    # 参数X
    #        sku：要检查的SKU
    #   lei_xingX权限或X权限，默认为1

    cn = get_cname()
    s=f"""SELECT count(*) 
            FROM ZiDian
           WHERE SKU='{sku}'  
                 and Dian in (SELECT Dian 
                                FROM DianQuanXian 
                               WHERE LeiXing={lei_xing}
                                     and YunYing=(SELECT UName
                                                    FROM ComputerName
                                                   WHERE cname='{cn}'))
        """
    return int(sf_db(s,True))>0

#########################################################################
def get_filtered_data_by_permission(base_sql, sku_column='ZhuSKU'):
    '''
    根据用户权限过滤数据查询结果
    参数X
        base_sql - 基础SQL查询语句
        sku_column - SKU字段名，默认XZhuSKU'
    返回：过滤后的查询结X
    '''
    accessible_skus = get_user_accessible_skus()

    if not accessible_skus:
        print("当前用户没有任何SKU访问权限")
        return []

    # 构建SKU权限过滤条件
    sku_filter = "','".join(accessible_skus)

    # 在原SQL基础上添加权限过X
    if 'where' in base_sql.lower():
        filtered_sql = f"{base_sql} AND {sku_column} IN ('{sku_filter}')"
    else:
        filtered_sql = f"{base_sql} WHERE {sku_column} IN ('{sku_filter}')"

    try:
        return sf_db(filtered_sql)
    except Exception as e:
        print(f"权限过滤查询失败：{e}")
        return []

#########################################################################
def show_user_permissions():
    '''
    显示当前用户的权限信X
    '''
    computer_name = get_cname()
    accessible_skus = get_user_accessible_skus()

    print(f"当前电脑名称：{computer_name}")
    print(f"可访问的SKU数量：{len(accessible_skus)}")

    if accessible_skus:
        print("可访问的SKU列表：")
        for i, sku in enumerate(accessible_skus, 1):
            print(f"  {i}. {sku}")
    else:
        print("当前用户没有任何SKU访问权限")
####################################################################
    import hashlib
    import base64
    from urllib.parse import quote
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.backends import default_backend

    def aes_encrypt_ecb_pkcs5(text, key):
        """使用cryptography库实现AES/ECB/PKCS5PADDING加密"""
        try:
            # 确保密钥长度X6字节X28位）
            if len(key) > 16:
                key = key[:16]
            elif len(key) < 16:
                key = key.ljust(16, '\0')

            key_bytes = key.encode('utf-8')
            text_bytes = text.encode('utf-8')

            # 创建AES加密器，使用ECB模式
            cipher = Cipher(algorithms.AES(key_bytes), modes.ECB(), backend=default_backend())
            encryptor = cipher.encryptor()

            # PKCS5PADDING填充
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(text_bytes)
            padded_data += padder.finalize()

            # 加密
            encrypted = encryptor.update(padded_data) + encryptor.finalize()

            # Base64编码
            encrypted_base64 = base64.b64encode(encrypted).decode('utf-8')
            return encrypted_base64

        except Exception as e:
            print(f"AES加密失败: {e}")
            return None

    def generate_sign_complete(params, app_id):
        """生成完整的签名（MD5 + AES/ECB/PKCS5PADDING + URL编码X

        Args:
            params (dict): 需要签名的参数字典
            app_id (str): 应用ID，用作AES加密密钥

        Returns:
            str: 最终签名字符串，如果失败返回None
        """
        try:
            print("\n=== 完整签名生成过程 ===")

            # 1. 过滤空值参X
            filtered_params = {}
            for key, value in params.items():
                if value is not None and value != '':
                    filtered_params[key] = value

            print(f"过滤后参X {filtered_params}")

            # 2. 按ASCII排序
            sorted_keys = sorted(filtered_params.keys())
            print(f"排序后的X {sorted_keys}")

            # 3. 拼接为key=value格式
            param_string = '&'.join([f"{key}={filtered_params[key]}" for key in sorted_keys])
            print(f"拼接字符X {param_string}")

            # 4. MD5加密并转大写（关键修复）
            md5_hash = hashlib.md5(param_string.encode('utf-8')).hexdigest().upper()
            print(f"MD5结果: {md5_hash}")

            # 5. AES加密（使用app_id作为密钥，关键修复）
            aes_result = aes_encrypt_ecb_pkcs5(md5_hash, app_id)
            print(f"AES加密结果: {aes_result}")

            # 6. URL编码
            final_sign = quote(aes_result, safe='')
            print(f"最终签X {final_sign}")

            return final_sign

        except Exception as e:
            print(f"签名生成失败: {e}")
            return None

#########################################################################
def db_to_dic(sql,delimiter='@'):
    '''
    开发日期：2025-08-14
    功能：指定SQL语句，将第一列作为Key值，之后所有的列作为Value值，用指定的拼接符链接，返回字典
          如果SQL只返X列，用这一列作为key，用''作为value
    '''
    l=sf_db(sql)                                    # 列表，里面嵌套元X
    mydic={}
    if isinstance(l[0], tuple):                     # 如果返回的l中的每个元素是元组，则说明返回的是多列数X
        for ele in l:                               # 将每个元组的第一个元素作为key，其他的元素拼接起来作为value
            s = ''
            for i in range(1,len(ele)):             # 将每个元组中从第2个元素开始，拼接起来
                s = s + str(ele[i]) + delimiter
            s=s[0:len(s)-len(delimiter)]            # 去掉最后面的连接符
            mydic[ele[0]] = s                       # 键值对添加到字典中
    else:                                           # 如果返回的l中的每个元素是字符串，则说明返回的是单列数据，用''作为valueX
        for ele in l: mydic[ele]=''
    return mydic

#########################################################################
def driver_number(driver='C'):
    # 开发日期：2025-08-19
    # 功能：返回指定盘符的序列号，默认为CX
    import ctypes
    vol_name_buf = ctypes.create_unicode_buffer(1024)
    fs_name_buf = ctypes.create_unicode_buffer(1024)
    serial_number = ctypes.c_ulong()
    flags = ctypes.c_ulong()
    max_component_length = ctypes.c_ulong()
    res = ctypes.windll.kernel32.GetVolumeInformationW(
          ctypes.c_wchar_p(driver+":\\"),vol_name_buf,
          ctypes.sizeof(vol_name_buf),ctypes.byref(serial_number),
          ctypes.byref(max_component_length),ctypes.byref(flags),
          fs_name_buf,ctypes.sizeof(fs_name_buf))

    if res == 0:raise ctypes.WinError()
    if serial_number.value >= 2**31:return abs(serial_number.value - 2**32)
    return abs(serial_number.value)

#########################################################################
def today(n=0):
    # 开发日期：2025-8-18
    # 功能：如果n=0或者默认，返回今天的日期；
    #      如果n<0，则返回今天之前n天的日期X
    #      如果n>0，返回今天n天之后的日期
    from datetime import datetime, timedelta
    return datetime.now().date()+timedelta(days=n)

#########################################################################
def date_delta(mydate,n):
    # 开发日期：2025-08-18
    # 功能：给定日期，返回该日Xn之后的日X
    from datetime import datetime, timedelta
    return mydate + timedelta(days=n)

#########################################################################
def send_message(chat_name, message, at_users=None, at_all=False, image_paths=None):
    """
    chat_name   : feishu_id.YONGHU 或 FeiShu_ID/open_id/chat_id
    message     : 消息文本
    at_users    : @的人名字列表（从feishu_id表查 FeiShu_ID，必须是 ou_xxxX
    at_all      : True 表示 @所有人
    image_paths : 图片路径列表（可以多张），默XNone
    """

    def esc(v): return '' if v is None else str(v).replace("'", "''")

    # ========= 从数据库Xchat_id / user_id =========
    chat_name = str(chat_name or "").strip()
    if chat_name.startswith(("ou_", "oc_")):
        fid = chat_name
    else:
        rows = sf_db(f"SELECT FeiShu_ID FROM FeiShu_ID WHERE YongHu='{esc(chat_name)}'")
        if not rows:
            print(f"X未找X{chat_name} XFeiShu_ID，请确认 FeiShu_ID 表有记录")
            return False
        fid = rows if isinstance(rows, str) else rows[0]

    # ========= 获取 token =========
    message_app_id = os.environ.get("FEISHU_MESSAGE_APP_ID")
    message_app_secret = os.environ.get("FEISHU_MESSAGE_APP_SECRET")
    if not message_app_id or not message_app_secret:
        print("X请先配置 FEISHU_MESSAGE_APP_ID 和 FEISHU_MESSAGE_APP_SECRET")
        return False

    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                      json={"app_id": message_app_id,
                            "app_secret": message_app_secret})
    access_token = r.json().get("tenant_access_token")
    if not access_token:
        print("X获取 token 失败", r.json())
        return False

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=utf-8"}
    msg_url = "https://open.feishu.cn/open-apis/im/v1/messages"
    img_url = "https://open.feishu.cn/open-apis/im/v1/images"

    # ========= 构建文本 / @消息 =========
    if at_users or at_all:
        # Xopen_id
        elements = [{"tag": "text", "text": message + " "}]

        if at_users:
            for uname in at_users:
                row2 = sf_db(f"SELECT FeiShu_ID FROM feishu_id WHERE YONGHU='{esc(uname)}'")
                if row2:
                    uid = row2 if isinstance(row2, str) else row2[0]
                    if uid.startswith("ou_"):
                        elements.append({"tag": "at", "user_id": uid})
                        elements.append({"tag": "text", "text": " "})

        if at_all:
            elements.append({"tag": "at", "user_id": "all"})
            elements.append({"tag": "text", "text": " "})

        payload = {
            "receive_id": fid,
            "msg_type": "post",
            "content": json.dumps({
                "zh_cn": {
                    "content": [elements]
                }
            }, ensure_ascii=False)
        }
    else:
        payload = {"receive_id": fid, "msg_type": "text", "content": json.dumps({"text": message}, ensure_ascii=False)}

    # ========= 发送文X/ @消息 =========
    r = requests.post(
        f"{msg_url}?receive_id_type={'chat_id' if fid.startswith('oc_') else 'open_id'}",
        headers=headers, json=payload).json()
    print("➡️ 文本/AT 发送结X", r)
    success = r.get("code") == 0

    # ========= 发送图片（多张X=========
    if image_paths:
        for img in image_paths:
            if not os.path.exists(img):
                print(f"⚠️ 图片不存X {img}")
                continue
            with open(img, "rb") as f:
                files = {"image": (os.path.basename(img), f, "image/png")}
                data = {"image_type": "message"}
                resp = requests.post(img_url, headers={"Authorization": f"Bearer {access_token}"}, files=files, data=data).json()
                image_key = resp.get("data", {}).get("image_key")
                if image_key:
                    img_payload = {"receive_id": fid, "msg_type": "image", "content": json.dumps({"image_key": image_key})}
                    r2 = requests.post(
                        f"{msg_url}?receive_id_type={'chat_id' if fid.startswith('oc_') else 'open_id'}",
                        headers=headers, json=img_payload).json()
                    print(f"➡️ 图片 {img} 发送结X", r2)
                    success = success and (r2.get("code") == 0)

    return success


#########################################################################
def create_yingyong_table():
    """
    Create YingYong table in TC database for workstation app entries.
    """
    sql_text = """
    IF OBJECT_ID(N'dbo.YingYong', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.YingYong (
            ID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            AppName NVARCHAR(100) NOT NULL,
            AppUrl NVARCHAR(500) NOT NULL,
            Portal NVARCHAR(50) NOT NULL,
            CreatedBy NVARCHAR(100) NULL,
            CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_YingYong_CreatedAt DEFAULT SYSDATETIME(),
            UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_YingYong_UpdatedAt DEFAULT SYSDATETIME(),
            IsActive BIT NOT NULL CONSTRAINT DF_YingYong_IsActive DEFAULT 1
        );

        CREATE INDEX IX_YingYong_Portal_IsActive
            ON dbo.YingYong (Portal, IsActive);
    END
    """
    return dui_db(sql_text)


#########################################################################
def get_yingyong_apps():
    """
    Return active workstation app entries from TC.dbo.YingYong.
    """
    rows = sf_db(
        """
        SELECT ID, AppName, AppUrl, Portal
          FROM dbo.YingYong
         WHERE IsActive = 1
         ORDER BY Portal, ID
        """
    )

    if not rows:
        return []

    if isinstance(rows, tuple):
        rows = [rows]

    apps = []
    for row in rows:
        app_id, name, url, portal = row
        apps.append(
            {
                "id": app_id,
                "name": name,
                "url": url,
                "portal": portal,
                "initials": str(name or "").strip()[:2].upper(),
            }
        )
    return apps


#########################################################################
def add_yingyong_app(name, url, portal, created_by=None):
    """
    Insert one workstation app entry into TC.dbo.YingYong.
    """
    SQL = """
    INSERT INTO dbo.YingYong (AppName, AppUrl, Portal, CreatedBy)
    OUTPUT INSERTED.ID
    VALUES (%s, %s, %s, %s)
    """
    conn = connect_tc_db()
    try:
        cursor = conn.cursor()
        cursor.execute(SQL, (name, url, portal, created_by))
        row = cursor.fetchone()
        if not conn.autocommit:
            conn.commit()
        app_id = row[0]
    except Exception:
        if not conn.autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "id": app_id,
        "name": name,
        "url": url,
        "portal": portal,
        "initials": str(name or "").strip()[:2].upper(),
    }


#########################################################################
def update_yingyong_app(app_id, name, url):
    """
    Update the name and URL for one active workstation app entry.
    """
    SQL = """
    UPDATE dbo.YingYong
       SET AppName = %s,
           AppUrl = %s,
           UpdatedAt = SYSDATETIME()
     WHERE ID = %s
       AND IsActive = 1
    """
    affected = dui_db(SQL, (name, url, app_id))
    if affected == 0:
        return None

    rows = sf_db(
        """
        SELECT ID, AppName, AppUrl, Portal
          FROM dbo.YingYong
         WHERE ID = %s
           AND IsActive = 1
        """,
        (app_id,),
    )
    if not rows:
        return None

    row = rows[0] if isinstance(rows, list) else rows
    app_id, app_name, app_url, portal = row
    return {
        "id": app_id,
        "name": app_name,
        "url": app_url,
        "portal": portal,
        "initials": str(app_name or "").strip()[:2].upper(),
    }


#########################################################################
def delete_yingyong_app(app_id):
    """
    Soft delete one workstation app entry.
    """
    SQL = """
    UPDATE dbo.YingYong
       SET IsActive = 0,
           UpdatedAt = SYSDATETIME()
     WHERE ID = %s
       AND IsActive = 1
    """
    return dui_db(SQL, (app_id,)) > 0


#########################################################################
def is_zhongkong_admin(user):
    """
    Check whether the Feishu user is listed as a WorkStation admin.
    """
    identities = [
        str(user.get("name") or "").strip(),
        str(user.get("openId") or "").strip(),
        str(user.get("unionId") or "").strip(),
        str(user.get("email") or "").strip(),
        str(user.get("mobile") or "").strip(),
    ]
    identities = [item for item in identities if item]
    if not identities:
        return False

    table_rows = sf_db(
        """
        SELECT TABLE_SCHEMA
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE LOWER(TABLE_NAME) = N'youjiantongzhi'
           AND LOWER(COLUMN_NAME) IN (N'shixiang', N'shoujianren')
         GROUP BY TABLE_SCHEMA
        HAVING COUNT(DISTINCT LOWER(COLUMN_NAME)) = 2
        """
    )
    if not table_rows:
        return False

    schema = table_rows[0] if isinstance(table_rows, list) else table_rows

    def quote_name(value):
        return f"[{str(value).replace(']', ']]')}]"

    table_name = f"{quote_name(schema)}.{quote_name('youjiantongzhi')}"

    rows = sf_db(
        f"""
    SELECT shoujianren
      FROM {table_name}
     WHERE shixiang = %s
       AND shoujianren IS NOT NULL
        """,
        ("中控平台管理员",),
    )
    if not rows:
        return False

    recipients = rows if isinstance(rows, list) else [rows]
    identity_set = set(identities)

    for recipient_text in recipients:
        names = re.split(r"[,，]", str(recipient_text or ""))
        if any(name.strip() in identity_set for name in names):
            return True

    return False
