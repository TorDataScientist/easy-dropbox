import os
import dropbox
import requests
import time
import glob
import tqdm

# アクセストークンの発行
def Issue_access_token(APP_KEY, APP_SECRET):
    print(f'https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code')
    AUTHORIZATION_CODE = input()
    data = {'code': AUTHORIZATION_CODE, 'grant_type': 'authorization_code'}
    response = requests.post('https://api.dropbox.com/oauth2/token', data=data, auth=(APP_KEY, APP_SECRET))
    DROPBOX_ACCESS_TOKEN = response.json()['access_token']
    return DROPBOX_ACCESS_TOKEN

# ドロップボックスを操作する
class EzDbx():
    def __init__(self, DROPBOX_ACCESS_TOKEN):
        # ここからAPIの使用を行っていく
        self.dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN, timeout=300)
        self.entry_list = []
        self.__tmp_entry_list = []

    # フォルダやファイル情報を可視化 ------------------------------------------------------------------------------------------
    def visible_path(self):
        return [entry.path_display for entry in self.entry_list]

    # 保存している entry_list の初期化 ----------------------------------------------------------------------------------------
    def __reset_entry_list(self):
        self.entry_list = []

    # フォルダやファイル情報を取得する ------------------------------------------------------------------------------------------
    # file_or_folder :str: ファイル情報のみ[file]か、フォルダ情報[folder]のみか、両方[all]かを選択する。
    # db_root_dir :str: '/'から始まるdb_root_dir以下の情報を取得する
    # recursive :str: 再帰的に取得するかどうか
    # save :str: entry_listにpathを保存するかどうか
    # reset :str: entry_listを初期化するかどうか
    # output :str: 最終的な可視化出力を行うかどうか
    def get_files(self, db_root_dir, file_or_folder, recursive = False, save = True, reset = True, output = True):
        self.__tmp_entry_list = []
        if reset : self.__reset_entry_list()
        try : res = self.dbx.files_list_folder(db_root_dir, recursive=recursive, limit = 2000) # 初めのアクセスを行う
        except : assert 'パスがありません。'
        self.__get_files_recursive(res, file_or_folder) # 再帰処理
        if save: self.entry_list = self.__tmp_entry_list # 保存を行う
        if output: return self.visible_path() # 戻り値

    # フォルダやファイル情報の再帰取得を行う
    def __get_files_recursive(self, res, file_or_folder):
        self.__save_path_list(res, file_or_folder)
        if res.has_more: # まだ追加取得があるかどうか
            res2 = self.dbx.files_list_folder_continue(res.cursor) # 続からのデータ取得
            self.__get_files_recursive(res2, file_or_folder) # 再読み込み

    # フォルダやファイルの情報を保存する
    def __save_path_list(self, res, file_or_folder):
        for entry in res.entries: # 戻り値に格納
            ins = type(entry)
            if file_or_folder == 'file':
                if ins is not dropbox.files.FileMetadata: continue #ファイル以外（＝フォルダ）はスキップ
                self.__tmp_entry_list.append(entry) # ファイル情報のみ保存
            elif file_or_folder == 'folder':
                if ins is dropbox.files.FileMetadata: continue # ファイルはスキップ
                self.__tmp_entry_list.append(entry) # フォルダ情報のみ保存
            elif file_or_folder == 'all': self.__tmp_entry_list.append(entry) # ファイル、フォルダ全て保存
            else: assert '第一引数に指定されていない文字列を使用しています。¥n使用可能な文字列は"file","folder","all"のいずれかです。'

    # 共有リンクを取得 ------------------------------------------------------------------------------------------------------------
    def get_shared_link(self, path):
        links = self.dbx.sharing_list_shared_links(path=path, direct_only=True).links
        if len(links) != 0:
            return links[0].url #1件目のURLを返す
        return self.__create_shared_link(path)

    # 共有リンクがない場合は作成
    def __create_shared_link(self, path):
        setting = dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
        link = self.dbx.sharing_create_shared_link_with_settings(path=path, settings=setting)
        return link.url

    # ファイルの書き込み ------------------------------------------------------------------------------------------------------------

    # ファイルのアップロードを行う関数
    # upload_path: '/' から始まる保存先
    # upload_file : 保存ファイル。フォルダなどから始まっても良いが、保存階層はupload_pathの直下にファイルが置かれる。
    # make_new_path : 保存先までのpathがない場合作成するかどうか
    # overwrite : 同じpathにファイルがある場合上書きするかどうか
    def upload(self, upload_path, upload_file, make_new_path = True, overwrite = False):
        if not self.__check_up_path(upload_path): # 保存先のpathがあるかどうかを調べる
            if make_new_path: self.make_folder(upload_path)
            else : assert '保存先までのパスがないためアップロードできません。' 
        db_upload_file = upload_file.split('/')[-1] # ファイル名
        with open(upload_file, "rb") as f: # ファイルをバイナリで開く
            file_size = os.path.getsize(upload_file) # ファイルの容量を調べる
            print(f'{db_upload_file} : {file_size} byte')
            chunk_size = 4 * 1024 * 1024
            if file_size <= chunk_size: self.__upload_file(upload_path, upload_file) # ファイルを普通に保存
            else: # 大容量の場合の保存方法
                with tqdm(total=file_size, desc="Uploaded") as pbar: # アップロードの可視化
                    upload_session_start_result = self.dbx.files_upload_session_start(f.read(chunk_size))
                    pbar.update(chunk_size)
                    cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id, offset=f.tell())
                    commit = dropbox.files.CommitInfo(path=f'{upload_path}/{db_upload_file}')
                    while f.tell() < file_size:
                        if (file_size - f.tell()) <= chunk_size: print(self.dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit))
                        else:
                            self.dbx.files_upload_session_append(f.read(chunk_size), cursor.session_id, cursor.offset)
                            cursor.offset = f.tell()
                        pbar.update(chunk_size)

    # 保存先のpathがあるかどうかを調べる
    def __check_up_path(self, upload_path):
        try : self.get_files(upload_path, 'all', recursive = True, save = False, reset = False, output = False) # 保存先のpathを再起的に取得する
        except : return False # upload_pathがない場合
        else : return True # upload_pathがある場合

    # フォルダ作成を行う
    def make_folder(self, upload_path):
        split_upload_path = upload_path.split('/')
        for i in range(2, len(split_upload_path) + 1):
            if not self.__check_up_path('/'.join(split_upload_path[:i])): self.dbx.files_create_folder('/'.join(split_upload_path[:i]))
        
    # ファイルのアップロードを行う
    def __upload_file(self, upload_path, upload_file):
        db_upload_file = upload_file.split('/')[-1] # ファイル名
        remote = f'{upload_path}/{db_upload_file}'
        with open(upload_file, 'rb') as f: self.dbx.files_upload(f.read(), remote)
        return True

    # ファイルの読み込み ------------------------------------------------------------------------------------------------------------
    
    # ファイルを変数として読み込む
    def read_file(self, read_file_path):
        metadata, f = self.dbx.files_download(read_file_path)
        return metadata, f

    # ファイルをダウンロードして保存する
    def download_file(self, read_file_path, save_path):
        try : self.dbx.files_download_to_file(save_path, read_file_path)
        except Exception as e : print(e)
        else : print('正常に保存されました。')