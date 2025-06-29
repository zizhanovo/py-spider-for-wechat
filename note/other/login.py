# encoding: utf-8
"""
微信公众号登录模块 - 独立登录功能

只包含登录相关的功能，避免加载不必要的依赖
"""

# 设置Windows兼容的UTF-8编码 - 增强版本
import sys
import os
import io
import locale

# 强制设置全局编码环境，解决Windows下所有编码问题
if sys.platform.startswith('win'):
    # 1. 设置控制台编码为UTF-8
    os.system('chcp 65001 >nul 2>&1')
    
    # 2. 设置环境变量强制UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
    
    # 3. 设置locale为UTF-8
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass
    
    # 4. 重新包装stdout和stderr为UTF-8（最强力的修复）
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, 
            encoding='utf-8', 
            errors='replace',
            newline='\n',
            line_buffering=True
        )
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, 
            encoding='utf-8', 
            errors='replace',
            newline='\n',
            line_buffering=True
        )
    
    # 5. 设置默认编码
    if hasattr(sys, '_getframe'):
        import codecs
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import os
import random
import time
import argparse
import platform
from datetime import datetime, timedelta
from selenium import webdriver
import requests
import re
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService

# 配置
CACHE_FILE = 'wechat_cache.json'
CACHE_EXPIRE_HOURS = 24 * 4  # 缓存有效期（小时），4天

def send_status(status, message, data=None):
    """向stdout发送JSON格式的状态更新"""
    payload = {"status": status, "message": message}
    if data:
        payload.update(data)
    print(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()

class WeChatLogin:
    """微信公众号登录管理器"""

    def __init__(self):
        self.token = None
        self.cookies = None
        self.cache_file = CACHE_FILE
        self.cache_expire_hours = CACHE_EXPIRE_HOURS

    def save_cache(self):
        """保存token和cookies到缓存文件"""
        if self.token and self.cookies:
            cache_data = {
                'token': self.token,
                'cookies': self.cookies,
                'timestamp': datetime.now().timestamp()
            }
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                print(f"[OK] 登录信息已保存到缓存文件 {self.cache_file}")
            except Exception as e:
                print(f"保存缓存失败: {e}")

    def load_cache(self):
        """从缓存文件加载token和cookies"""
        if not os.path.exists(self.cache_file):
            print("缓存文件不存在，需要重新登录")
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromtimestamp(cache_data['timestamp'])
            current_time = datetime.now()
            hours_diff = (current_time - cache_time).total_seconds() / 3600
            
            if hours_diff > self.cache_expire_hours:
                print(f"缓存已过期（{hours_diff:.1f}小时前），需要重新登录")
                return False
            
            self.token = cache_data['token']
            self.cookies = cache_data['cookies']
            print(f"[OK] 从缓存加载登录信息（{hours_diff:.1f}小时前保存）")
            return True
            
        except Exception as e:
            print(f"读取缓存失败: {e}，需要重新登录")
            return False
    
    def validate_cache(self):
        """验证缓存的token和cookies是否仍然有效"""
        if not self.token or not self.cookies:
            return False
        
        try:
            header = {
                "HOST": "mp.weixin.qq.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            }
            
            test_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz'
            test_params = {
                'action': 'search_biz', 'token': self.token, 'lang': 'zh_CN', 'f': 'json', 'ajax': '1',
                'random': random.random(), 'query': 'test', 'begin': '0', 'count': '1',
            }
            
            response = requests.get(test_url, cookies=self.cookies, headers=header, params=test_params, timeout=10)
            response.raise_for_status()

            result = response.json()
            
            if 'base_resp' in result:
                if result['base_resp']['ret'] == 0:
                    print("[OK] 缓存的登录信息验证有效")
                    return True
                elif result['base_resp']['ret'] in (-6, 200013):
                    print("[FAIL] 缓存的token已失效")
                    return False
                else:
                    print(f"[FAIL] 验证失败: {result['base_resp'].get('err_msg', '未知错误')}")
                    return False
            else:
                print("[FAIL] 验证响应格式异常")
                return False
                
        except json.JSONDecodeError as e:
            print(f"[FAIL] 验证缓存时解析JSON出错: {e}")
            return False
        except Exception as e:
            print(f"[FAIL] 验证缓存时发生未知错误: {e}")
            return False

    def clear_cache(self):
        """清除缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                print("缓存文件已清除")
        except Exception as e:
            print(f"清除缓存失败: {e}")

    def check_login_status(self):
        """检查当前登录状态"""
        if self.load_cache() and self.validate_cache():
            cache_time = None
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                cache_time = datetime.fromtimestamp(cache_data['timestamp'])
            except:
                pass
            
            return {
                'isLoggedIn': True,
                'loginTime': cache_time.strftime('%Y-%m-%d %H:%M:%S') if cache_time else '',
                'cacheExpiry': (cache_time + timedelta(hours=self.cache_expire_hours)).strftime('%Y-%m-%d %H:%M:%S') if cache_time else ''
            }
        else:
            return {'isLoggedIn': False}

    def login(self):
        """登录微信公众号平台"""
        print("\n" + "="*60 + "\n开始登录微信公众号平台...\n" + "="*60)
        
        if self.load_cache() and self.validate_cache():
            print("[OK] 使用有效的缓存登录信息")
            print("LOGIN_SUCCESS")
            return True
        else:
            print("缓存无效或不存在，需要重新扫码登录")
            self.clear_cache()
        
        print("\n开始浏览器登录...")
        driver = None
        try:
            # Windows环境下先清理可能残留的Chrome进程
            if platform.system() == "Windows":
                try:
                    import subprocess
                    print("正在清理可能残留的Chrome进程...")
                    subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
                    subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                    time.sleep(1)  # 等待进程完全关闭
                except Exception as e:
                    print(f"清理进程时出现警告: {e}")
            
            # 配置Chrome选项，使其更适合自动化，并尝试规避检测
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
            
            # 为每次登录使用不同的用户数据目录，避免冲突
            import tempfile
            user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
            # Windows路径处理，避免转义问题
            user_data_dir = user_data_dir.replace("\\", "/")
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            
            # 关键：尝试隐藏自动化特征
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 最小化的媒体禁用配置，仅解决ffmpeg.dll问题
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 其他一些常规选项
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument("--start-maximized") # 启动时最大化窗口
            
            # Windows特定的Chrome配置
            if platform.system() == "Windows":
                chrome_options.add_argument('--remote-debugging-port=0')  # 使用随机端口
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # 添加更详细的日志
            print("正在启动Chrome浏览器...")
            send_status("info", "正在启动Chrome浏览器...")
            
            # Windows环境下的特殊检查
            if platform.system() == "Windows":
                print("检测到Windows环境，正在检查Chrome安装...")
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                ]
                chrome_found = False
                for path in chrome_paths:
                    if os.path.exists(path):
                        print(f"[OK] 找到Chrome: {path}")
                        chrome_found = True
                        break
                
                if not chrome_found:
                    error_msg = "未找到Chrome浏览器，请先安装Google Chrome"
                    print(f"[FAIL] {error_msg}")
                    send_status("error", error_msg)
                    return False
            
            send_status("info", "正在初始化ChromeDriver...")
            print("正在初始化ChromeDriver...")
            
            # 直接使用内置的chromedriver
            driver_path = ''
            if platform.system() == "Windows":
                print(f"调试信息 - sys.executable路径: {sys.executable}")
                print(f"调试信息 - sys.executable目录: {os.path.dirname(sys.executable)}")
                print(f"调试信息 - 当前脚本路径: {__file__}")
                print(f"调试信息 - 当前脚本目录: {os.path.dirname(__file__)}")
                
                # 方法1：基于当前脚本位置查找（在Electron应用中更可靠）
                script_dir = os.path.dirname(os.path.abspath(__file__))
                driver_path = os.path.join(script_dir, 'venv', 'Scripts', 'chromedriver.exe')
                print(f"调试信息 - 方法1路径: {driver_path}")
                print(f"调试信息 - 方法1存在: {os.path.exists(driver_path)}")
                
                if not os.path.exists(driver_path):
                    # 方法2：基于sys.executable位置查找
                    driver_path = os.path.join(os.path.dirname(sys.executable), 'chromedriver.exe')
                    print(f"调试信息 - 方法2路径: {driver_path}")
                    print(f"调试信息 - 方法2存在: {os.path.exists(driver_path)}")
                    
                    if not os.path.exists(driver_path):
                        # 方法3：相对于sys.executable的Scripts目录
                        driver_path = os.path.join(os.path.dirname(sys.executable), '..', 'Scripts', 'chromedriver.exe')
                        print(f"调试信息 - 方法3路径: {driver_path}")
                        print(f"调试信息 - 方法3存在: {os.path.exists(driver_path)}")
                        
                        if not os.path.exists(driver_path):
                            # 方法4：尝试其他可能的相对路径
                            possible_paths = [
                                os.path.join(script_dir, '..', 'backend', 'venv', 'Scripts', 'chromedriver.exe'),
                                os.path.join(script_dir, 'Scripts', 'chromedriver.exe'),
                                os.path.join(os.path.dirname(sys.executable), 'backend', 'venv', 'Scripts', 'chromedriver.exe'),
                                os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'backend', 'venv', 'Scripts', 'chromedriver.exe')
                            ]
                            
                            for possible_path in possible_paths:
                                print(f"调试信息 - 尝试路径: {possible_path}")
                                print(f"调试信息 - 路径存在: {os.path.exists(possible_path)}")
                                if os.path.exists(possible_path):
                                    driver_path = possible_path
                                    break

            if driver_path and os.path.exists(driver_path):
                print(f"✅ 使用内置的ChromeDriver: {driver_path}")
                service = ChromeService(executable_path=driver_path)
            else:
                # 如果找不到内置的，回退到SeleniumManager
                print("❌ 未找到内置的ChromeDriver，回退到Selenium Manager...")
                print("这可能是因为路径查找逻辑需要调整")
                service = ChromeService()

            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome 浏览器实例创建成功")

            # 进一步隐藏特征
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print("正在访问微信公众号平台...")
            driver.get('https://mp.weixin.qq.com/')
            print("页面加载完成")
            
            send_status("browser-opened", "浏览器已打开，请在浏览器窗口中扫码登录")

            # 使用WebDriverWait主动等待登录成功，最长等待5分钟
            wait = WebDriverWait(driver, 300) 
            
            # 等待URL中出现'token'，这是登录成功的明确标志
            wait.until(EC.url_contains('token'))
            
            # 到这里说明登录成功了
            current_url = driver.current_url
            print("[OK] 检测到登录成功！正在获取登录信息...")
            
            # 提取token
            token_match = re.search(r'token=(\d+)', current_url)
            if token_match:
                self.token = token_match.group(1)
                print(f"[OK] Token获取成功: {self.token}")
            else:
                print("[FAIL] 无法从URL中提取token, 登录失败")
                send_status("error", "无法从URL中提取token")
                driver.quit()
                
                # 清理临时用户数据目录
                try:
                    import shutil
                    if 'user_data_dir' in locals() and os.path.exists(user_data_dir):
                        shutil.rmtree(user_data_dir, ignore_errors=True)
                        print("临时用户数据目录已清理")
                except Exception as e:
                    print(f"清理临时目录时出现警告: {e}")
                
                return False

            # 获取cookies
            self.cookies = {item['name']: item['value'] for item in driver.get_cookies()}
            print(f"[OK] Cookies获取成功，共{len(self.cookies)}个")
            
            # 保存到缓存
            self.save_cache()
            
            print("[OK] 登录完成！浏览器已自动关闭")
            send_status("success", "登录成功！")
            driver.quit()
            
            # 清理临时用户数据目录
            try:
                import shutil
                if 'user_data_dir' in locals() and os.path.exists(user_data_dir):
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                    print("临时用户数据目录已清理")
            except Exception as e:
                print(f"清理临时目录时出现警告: {e}")
            
            return True
            
        except Exception as e:
            print(f"登录过程中出现错误: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            # Windows环境下强制清理Chrome进程
            if platform.system() == "Windows":
                try:
                    import subprocess
                    print("强制清理Chrome进程...")
                    subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
                    subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                except Exception as cleanup_error:
                    print(f"清理进程时出现警告: {cleanup_error}")
            
            # 清理临时用户数据目录
            try:
                import shutil
                if 'user_data_dir' in locals() and os.path.exists(user_data_dir):
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                    print("临时用户数据目录已清理")
            except Exception as e:
                print(f"清理临时目录时出现警告: {e}")
            
            # 根据错误类型发送不同的状态信息
            if "timeout" in str(e).lower() or "TimeoutException" in str(type(e).__name__):
                print("LOGIN_TIMEOUT")
                send_status("timeout", f"登录等待超时: {e}")
            else:
                print("LOGIN_ERROR")
                send_status("error", f"登录过程中出现错误: {e}")
            return False

    def logout(self):
        """退出登录"""
        print("正在退出登录...")
        
        # 清除缓存和状态
        self.clear_cache()
        self.token = None
        self.cookies = None
        
        # Windows环境下清理可能残留的Chrome进程
        if platform.system() == "Windows":
            try:
                import subprocess
                print("清理残留的Chrome进程...")
                subprocess.run("taskkill /f /im chrome.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /f /im chromedriver.exe", shell=True, capture_output=True)
                print("Chrome进程清理完成")
            except Exception as e:
                print(f"清理进程时出现警告: {e}")
        
        print("退出登录完成")
        return True

def save_token_to_cache(token):
    """保存token到缓存文件"""
    cache_data = {
        'token': token,
        'cookies': {},  # 暂时为空，需要完整登录才有cookies
        'timestamp': datetime.now().timestamp()
    }
    
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_cache.json')
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    print("LOGIN_SUCCESS")
    return True

def check_login_status():
    """检查登录状态"""
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_cache.json')
    
    if not os.path.exists(cache_file):
        return {"is_logged_in": False, "message": "未找到登录缓存"}
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查新格式（timestamp）
        if 'timestamp' in cache_data:
            cache_time = datetime.fromtimestamp(cache_data['timestamp'])
            current_time = datetime.now()
            hours_diff = (current_time - cache_time).total_seconds() / 3600
            expire_time = cache_time + timedelta(hours=96)  # 4天后过期
            
            # 缓存有效期4天（96小时）
            if hours_diff > 96:
                return {
                    "is_logged_in": False, 
                    "message": "登录已过期",
                    "login_time": cache_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "expire_time": expire_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "hours_since_login": round(hours_diff, 1)
                }
            
            return {
                "is_logged_in": True, 
                "login_time": cache_time.strftime('%Y-%m-%d %H:%M:%S'),
                "expire_time": expire_time.strftime('%Y-%m-%d %H:%M:%S'),
                "hours_since_login": round(hours_diff, 1),
                "hours_until_expire": round(96 - hours_diff, 1),
                "token": cache_data.get('token', ''),
                "message": f"已登录 {round(hours_diff, 1)} 小时"
            }
        
        # 兼容旧格式（expires_at）
        elif 'expires_at' in cache_data:
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.now() > expires_at:
                return {"is_logged_in": False, "message": "登录已过期"}
                
            return {
                "is_logged_in": True, 
                "login_time": cache_data.get('login_time', '未知'),
                "token": cache_data.get('token', '')
            }
        else:
            return {"is_logged_in": False, "message": "缓存格式错误"}
            
    except Exception as e:
        return {"is_logged_in": False, "message": f"读取缓存失败: {str(e)}"}

def clear_login_cache():
    """清除登录缓存"""
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wechat_cache.json')
    
    if os.path.exists(cache_file):
        os.remove(cache_file)
        return {"success": True, "message": "登录缓存已清除"}
    else:
        return {"success": True, "message": "无需清除，缓存文件不存在"}

def main():
    parser = argparse.ArgumentParser(description='微信公众号登录管理')
    parser.add_argument('--check-status', action='store_true', help='检查登录状态')
    parser.add_argument('--save-token', type=str, help='保存token到缓存')
    parser.add_argument('--clear-cache', action='store_true', help='清除登录缓存')
    parser.add_argument('--start-login', action='store_true', help='启动登录流程')
    parser.add_argument('--logout', action='store_true', help='退出登录')
    
    args = parser.parse_args()
    
    if args.check_status:
        status = check_login_status()
        print(json.dumps(status, ensure_ascii=False))
    elif args.save_token:
        save_token_to_cache(args.save_token)
    elif args.clear_cache:
        result = clear_login_cache()
        print(json.dumps(result, ensure_ascii=False))
    elif args.start_login:
        # 启动登录流程
        login_manager = WeChatLogin()
        if login_manager.login():
            print("LOGIN_SUCCESS")
        else:
            print("LOGIN_FAILED")
    elif args.logout:
        # 退出登录
        login_manager = WeChatLogin()
        if login_manager.logout():
            print("LOGOUT_SUCCESS")
            print(json.dumps({"success": True, "message": "已退出登录"}, ensure_ascii=False))
        else:
            print(json.dumps({"success": False, "message": "退出登录失败"}, ensure_ascii=False))
    else:
        # 默认启动登录流程（保持兼容性）
        print("请使用内嵌登录界面进行登录")

if __name__ == "__main__":
    main() 