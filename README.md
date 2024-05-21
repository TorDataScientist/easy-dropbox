
<div align="center">
<img src="https://user-images.githubusercontent.com/45032597/138818248-359196b7-0015-4f15-9888-e282d80c5887.png" height="200" align="center">
</div>
<h1 align="center"><b>easy-dropbox</b></h1>

**I have summarized the operations that are often used in drop boxes for ease of use!**  
**ドロップボックスでよく使われる操作を使いやすいようにまとめました！**

![](https://img.shields.io/pypi/v/ez-dropbox?style=plastic)
![](https://img.shields.io/github/forks/TorDataScientist/ez-dropbox?style=plastic)
![](https://img.shields.io/github/license/TorDataScientist/ez-dropbox?style=plastic)


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
- Synchronize folders between local and Dropbox (ローカルフォルダとDropboxの同期)
- Download files (ファイルのダウンロード)
- Delete, move, copy files and folders (ファイルやフォルダの削除、移動、コピー)
- Get file or folder metadata (ファイルやフォルダのメタデータ取得)

# **Installation[インストール]**

```bash
pip install ez-dropbox
```

# **Use library[ライブラリの使用方法]**

```python 
import ezdbx
```

# 1. Initial setting[初期設定]
## 1.1. Issuance of access token[アクセストークンの発行]
```python
ACCESS_TOKEN = ezdbx.issue_access_token(APP_KEY, APP_SECRET)
```

## 1.2. Create an instance[インスタンスの作成]
```python
ed = ezdbx.EzDbx(ACCESS_TOKEN)
```

# 2. Dropbox operation[Dropboxの操作]
## 2.1. Folder / file search[フォルダ・ファイル検索]
```python
ed.ls(file_or_folder='all')
```

## 2.2. Create a new folder[フォルダの作成]
```python
ed.mkdir('/app/sample/new_folder1/new_folder2')
```

## 2.3. Save file[ファイルの保存]
```python
ed.upload('/home/user/sample.txt', '/app/sample/folder1/folder2', overwrite=True)
```

## 2.4. Generating shared links for folders and files[フォルダ・ファイルの共有リンクの生成]
```python
link = ed.get_shared_link('/app/sample/folder1')
print(link)
```

## 2.5. Synchronize local folder with Dropbox folder[ローカルフォルダとDropboxフォルダの同期]
### 2.5.1 Write Sync (Local to Dropbox)[ローカルからDropboxへの同期]
```python
ed.write_sync('/local/path/to/folder', '/dropbox/path/to/folder')
```

### 2.5.2 Read Sync (Dropbox to Local)[Dropboxからローカルへの同期]
```python
ed.read_sync('/local/path/to/folder', '/dropbox/path/to/folder')
```

## 2.6. Download files[ファイルのダウンロード]
```python
ed.download_file('/dropbox/path/to/file', '/local/path/to/save/file')
```

## 2.7. Delete, move, copy files and folders[ファイルやフォルダの削除、移動、コピー]
### 2.7.1 Delete a file or folder[ファイルやフォルダの削除]
```python
ed.delete_file_or_folder('/dropbox/path/to/file_or_folder')
```

### 2.7.2 Move a file or folder[ファイルやフォルダの移動]
```python
ed.move_file_or_folder('/dropbox/path/from', '/dropbox/path/to')
```

### 2.7.3 Copy a file or folder[ファイルやフォルダのコピー]
```python
ed.copy_file_or_folder('/dropbox/path/from', '/dropbox/path/to')
```

## 2.8. Get file or folder metadata[ファイルやフォルダのメタデータ取得]
```python
metadata = ed.get_file_metadata('/dropbox/path/to/file_or_folder')
print(metadata)
```

# **Error Handling for Unsupported Files[サポートされていないファイルのエラーハンドリング]**
If the file cannot be written directly, it will be compressed into a ZIP file and then uploaded. This helps handle files that are not directly supported or have special requirements.
(ファイルが直接書き込めない場合は、ZIPファイルに圧縮してからアップロードされます。これにより、直接サポートされていないファイルや特別な要件があるファイルを処理できます。)

Example[例]:
```python
try:
    ed.upload('/path/to/unsupported_file.gsheet', '/dropbox/path')
except Exception as e:
    print(f'Error uploading file: {e}')
```
