<div align="center">
<img src="https://user-images.githubusercontent.com/45032597/138818248-359196b7-0015-4f15-9888-e282d80c5887.png" height="200" align="center">
</div>
<h1 align="center"><b>easy-dropbox</b></h1>

**I have summarized the operations that are often used in drop boxes for ease of use!**  
**ドロップボックスでよく使われる操作を使いやすいようにまとめました！**

![](https://img.shields.io/pypi/v/easy-dropbox?style=plastic)
![](https://img.shields.io/github/forks/TorDataScientist/easy-dropbox?style=plastic)
![](https://img.shields.io/github/license/TorDataScientist/easy-dropbox?style=plastic)


# **OutLine[概要]**
I want to do various things with the DropBox API, but I still find it difficult.(DropBoxAPIで色々やりたいけど、自分にはまだ難しく感じる。)  

First of all, this is for you ❗️(そんなあなたにまずはこれ❗️)  
Manage DropBox with easy operation 😁(簡単操作でDropBoxを管理しよう😁)

Here's what you can do with easy-dropbox today:  
(現在easy-dropboxで可能なことは以下になります。)
- Folder / file search(フォルダ・ファイル検索)
- Create a new folder(フォルダの作成)
- Save file(ファイルの保存)
- Generating shared links for folders and files(フォルダ・ファイルの共有リンクの生成)

# **Installation[インストール]**

```bash
pip install easy-dropbox
```

# **Use library[ライブラリの使用方法]**

```python 
import ezdbx
```

# 1. Initial setting[初期設定]
## 1.1. Issuance of access token[アクセストークンの発行]
```python
ACCESS_TOKEN = ezdbx.Issue_access_token(APP_KEY, APP_SECRET)
```

## 1.2. Create an instance[インスタンスの作成]
```python
ed = ezdbx.EzDbx(ACCESS_TOKEN)
```
# 2. Dropbox operation[Dropboxの操作]
## 2.1. Folder / file search[フォルダ・ファイル検索]
```python
db_root_dir = ['Which folder to search in.(どのフォルダ内を検索するか)']　# exsample '/app/sample'
file_or_folder = ['Whether to get files only, folders only, or all.(ファイルのみか、フォルダのみか、全てを取得するか)'] # 'file' or 'folder' or 'all'
ed.get_files(db_root_dir, file_or_folder, recursive = False, save = True, reset = True, output = True)
```
## 2.2. Create a new folder[フォルダの作成]
```python
upload_path # esample : '/app/sample/new_folder1/new_folder2'
ed.make_folder(upload_path)
```
## 2.3. Save file[ファイルの保存]
```python
upload_path # esample : '/app/sample/folder1/folder2'
upload_file # esample : '/home/user/sample.txt'
ed.upload(upload_path, upload_file, make_new_path = True):
```
## 2.4. Generating shared links for folders and files[フォルダ・ファイルの共有リンクの生成]
```python
path = ['File or folder path(ファイルもしくはフォルダのパス)'] # esample : '/app/sample/folder1'
ed.get_shared_link(path)
```


