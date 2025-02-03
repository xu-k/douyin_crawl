import os

# 设置目标文件夹路径
folder_path = 'D:\Project\douyin_crawl-main\chagee'

# 支持的图片文件格式
image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
# 支持的视频文件格式
video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv']

# 获取文件夹中的所有文件
files = os.listdir(folder_path)

# 按文件类型分类
image_files = [f for f in files if any(f.lower().endswith(ext) for ext in image_extensions)]
video_files = [f for f in files if any(f.lower().endswith(ext) for ext in video_extensions)]

# 合并图片和视频文件列表，并按文件名排序
all_files = sorted(image_files + video_files)

# 按顺序重命名文件
for index, file_name in enumerate(all_files, start=1):
    # 获取文件扩展名
    file_ext = os.path.splitext(file_name)[1]
    # 新的文件名
    new_name = f"{index}{file_ext}"
    # 构建旧文件和新文件的完整路径
    old_file_path = os.path.join(folder_path, file_name)
    new_file_path = os.path.join(folder_path, new_name)
    # 重命名文件
    os.rename(old_file_path, new_file_path)

    print(f"Renamed: {file_name} -> {new_name}")

print("文件重命名完成！")
