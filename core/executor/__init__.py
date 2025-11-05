import os
from urllib.parse import urlparse

if __name__ == "__main__":
    url = "https://asynctest.oss-cn-shenzhen.aliyuncs.com/core/project_files/1/2025/09/04/be0c9cbe-8b84-479b-863f-de0c08f0feeb-我的图的svg.svg"
    path = urlparse(url).path
    filename = os.path.basename(path)
    print(filename)
