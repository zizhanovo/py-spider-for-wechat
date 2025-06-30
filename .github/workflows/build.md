name: 构建多平台可执行文件

on:
  workflow_dispatch:  # 手动触发
  push:
    tags:
      - 'v*'  # 当推送版本标签时触发

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: windows-latest
            platform: windows
            python-version: '3.11'
          - os: macos-latest
            platform: macos
            python-version: '3.11'
          - os: ubuntu-latest
            platform: linux
            python-version: '3.11'

    steps:
    - name: 检出代码
      uses: actions/checkout@v4

    - name: 设置Python环境
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: 升级pip
      run: python -m pip install --upgrade pip

    - name: 安装基础依赖
      run: |
        pip install pyinstaller
        pip install pillow

    - name: 安装项目依赖
      run: |
        pip install requests beautifulsoup4 tqdm PyQt5 selenium
      continue-on-error: true

    - name: 创建简单图标
      run: |
        python -c "
        from PIL import Image, ImageDraw
        import os
        os.makedirs('img', exist_ok=True)
        size = 256
        img = Image.new('RGBA', (size, size), (7, 193, 96))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 206, 206], fill=(255, 255, 255), width=3)
        for i in range(4):
            x = 70 + i * 30
            draw.line([(x, 70), (x, 186)], fill=(7, 193, 96), width=2)
            y = 70 + i * 30
            draw.line([(70, y), (186, y)], fill=(7, 193, 96), width=2)
        img.save('img/icon.png', 'PNG')
        print('图标创建完成')
        "

    - name: 创建ICO文件 (Windows)
      if: matrix.platform == 'windows'
      run: |
        python -c "
        from PIL import Image
        img = Image.open('img/icon.png')
        sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        ico_imgs = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
        ico_imgs[0].save('img/icon.ico', format='ICO', sizes=sizes)
        print('ICO文件创建完成')
        "

    - name: 构建Windows可执行文件
      if: matrix.platform == 'windows'
      run: |
        pyinstaller --onefile --windowed --name="微信爬虫工具" --distpath="./dist" main.py
      continue-on-error: true

    - name: 构建macOS可执行文件
      if: matrix.platform == 'macos'
      run: |
        pyinstaller --onefile --windowed --name="微信爬虫工具" --distpath="./dist" main.py
      continue-on-error: true

    - name: 构建Linux可执行文件
      if: matrix.platform == 'linux'
      run: |
        pyinstaller --onefile --name="微信爬虫工具" --distpath="./dist" main.py
      continue-on-error: true

    - name: 检查构建结果
      run: |
        echo "检查dist目录内容："
        ls -la dist/ || dir dist\ || echo "dist目录不存在"

    - name: 准备发布文件 (Windows)
      if: matrix.platform == 'windows'
      shell: bash
      run: |
        mkdir -p release
        if [ -f "dist/微信爬虫工具.exe" ]; then
          cp "dist/微信爬虫工具.exe" release/
          echo "Windows exe文件已复制"
        elif [ -f "dist/微信爬虫工具" ]; then
          cp "dist/微信爬虫工具" release/微信爬虫工具.exe
          echo "Windows 可执行文件已复制并重命名"
        else
          echo "未找到Windows可执行文件"
          ls -la dist/
        fi

    - name: 准备发布文件 (macOS)
      if: matrix.platform == 'macos'
      run: |
        mkdir -p release
        if [ -f "dist/微信爬虫工具" ]; then
          cp "dist/微信爬虫工具" release/微信爬虫工具-macos
          echo "macOS 可执行文件已复制"
        else
          echo "未找到macOS可执行文件"
          ls -la dist/
        fi

    - name: 准备发布文件 (Linux)
      if: matrix.platform == 'linux'
      run: |
        mkdir -p release
        if [ -f "dist/微信爬虫工具" ]; then
          cp "dist/微信爬虫工具" release/微信爬虫工具-linux
          chmod +x release/微信爬虫工具-linux
          echo "Linux 可执行文件已复制"
        else
          echo "未找到Linux可执行文件"
          ls -la dist/
        fi

    - name: 上传构建产物
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: 微信爬虫工具-${{ matrix.platform }}
        path: |
          release/
          dist/
        retention-days: 30 