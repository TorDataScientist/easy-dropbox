import os
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
import requests
import time
import glob
import joblib
from tqdm import tqdm

# Issuance of access token. (アクセストークンの発行)
def issue_access_token(APP_KEY, APP_SECRET):
    print(f'https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code')
    AUTHORIZATION_CODE = input('AUTHORIZATION_CODE : ')
    data = {'code': AUTHORIZATION_CODE, 'grant_type': 'authorization_code'}
    response = requests.post('https://api.dropbox.com/oauth2/token', data=data, auth=(APP_KEY, APP_SECRET))
    DROPBOX_ACCESS_TOKEN = response.json()['access_token']
    return DROPBOX_ACCESS_TOKEN

# 更新トークンファイルの生成
def create_refresh_access_token_file(APP_KEY, APP_SECRET, save_file_path):
    auth_flow = DropboxOAuth2FlowNoRedirect(
                            APP_KEY,
                            consumer_secret=APP_SECRET, # PKCEがFalseの場合に必要
                            use_pkce=False, # Trueだとシークレットキーは不要
                            token_access_type='offline'
    )
    print(auth_flow.start())
    print('Access URL and get authentication code')
    authentication_code = input('authentication code : ')
    oauth_result = auth_flow.finish(authentication_code)
    rdbx = dropbox.Dropbox(oauth2_refresh_token=oauth_result.refresh_token, app_key=APP_KEY, app_secret=APP_SECRET)
    rdbx.users_get_current_account()
    joblib.dump(rdbx, save_file_path, compress=3)

    print(f'create {save_file_path} success!')

# 更新トークンファイルでアクセスキーの更新＆取得
def refresh_token(load_path):
    rdbx = joblib.load(load_path)
    rdbx.refresh_access_token()
    joblib.dump(rdbx, load_path, compress=3)
    print(f'update {load_path} success!')
    return rdbx._oauth2_access_token

# Class that operates the drop box. (ドロップボックスを操作するクラス)
class EzDbx():
    def __init__(self, DROPBOX_ACCESS_TOKEN):
        self.dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN, timeout=300)
        self.entry_list = [] 
        self.__tmp_entry_list = []
        self.error_file_path = []

    # Get folder and file information. (フォルダやファイル情報を取得する) ------------------------------------------------------------------------------------------
    def get_files(self, db_root_dir, file_or_folder, recursive = False, save = True, reset = True, output = True):
        '''
        db_root_dir[str]: Get the following information from db_root_dir starting with'/'. ('/'から始まるdb_root_dir以下の情報を取得する)
        file_or_folder['file' or 'folder' or 'all']: Select file information only, folder information only, or both. (ファイル情報のみ、フォルダ情報のみ、両方を選択する。)
        recursive[bool]: Whether to get recursively. (再帰的に取得するかどうか)
        save[bool]: Whether to save the entry in entry_list. (entry_listにpathを保存するかどうか)
        reset[bool]: Whether to initialize entry_list. (entry_listを初期化するかどうか)
        output[bool]: Whether to do the final visualization output. (最終的な可視化出力を行うかどうか)
        '''
        self.__tmp_entry_list = []
        res = ''
        if reset : self.__reset_entry_list()
        try : 
          res = self.dbx.files_list_folder(db_root_dir, recursive=recursive, limit = 2000) # 初めのアクセスを行う
          self.__save_path_list(res, file_or_folder)
          if res.has_more: self.__get_files_recursive(res, file_or_folder) # Recursive processing. (再帰処理)
          if save: self.entry_list = self.__tmp_entry_list # Save. (保存を行う)
          if output: return self.visible_path() # Return value. (戻り値)
        except : assert False, 'There is no path. (パスがありません。)'

    # Recursive acquisition of folder and file information. (フォルダやファイル情報の再帰取得を行う)
    def __get_files_recursive(self, res, file_or_folder):
        if res.has_more: # Whether there are still additional acquisitions. (まだ追加取得があるかどうか)
            res2 = self.dbx.files_list_folder_continue(res.cursor)
            self.__save_path_list(res2, file_or_folder)
            self.__get_files_recursive(res2, file_or_folder) 

    # Save folder and file information. (フォルダやファイルの情報を保存する)
    def __save_path_list(self, res, file_or_folder):
        for entry in res.entries:
            ins = type(entry)
            if file_or_folder == 'file':
                if ins is not dropbox.files.FileMetadata: continue 
                self.__tmp_entry_list.append(entry) 
            elif file_or_folder == 'folder':
                if ins is dropbox.files.FileMetadata: continue 
                self.__tmp_entry_list.append(entry)
            elif file_or_folder == 'all': self.__tmp_entry_list.append(entry) 
            else: assert False, 'You are using a string that is not specified in the first argument.\n第一引数に指定されていない文字列を使用しています。\nAvailable strings are "file", "folder", "all".\n使用可能な文字列は"file","folder","all"のいずれかです。'

    # Visualize read folder and file information. (読み込んだフォルダやファイル情報を可視化) ------------------------------------------------------------------------------------------
    def visible_path(self):
        return [entry.path_display for entry in self.entry_list]

    # Initialize the saved entry_list. (保存している entry_list の初期化) ----------------------------------------------------------------------------------------
    def __reset_entry_list(self):
        self.entry_list = []

    # Get a shared link.(共有リンクを取得) ------------------------------------------------------------------------------------------------------------
    def get_shared_link(self, path):
        links = self.dbx.sharing_list_shared_links(path=path, direct_only=True).links
        if len(links) != 0: return links[0].url
        return self.__create_shared_link(path)

    # Create if there is no shared link. (共有リンクがない場合は作成)
    def __create_shared_link(self, path):
        setting = dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
        link = self.dbx.sharing_create_shared_link_with_settings(path=path, settings=setting)
        return link.url

    # File upload. (ファイルのウップロード) ------------------------------------------------------------------------------------------------------------

    def upload(self, upload_path, upload_file, make_new_path = True, overwrite = False, skip = False):
        '''
        Function to upload a file. (ファイルのアップロードを行う関数)
        upload_path[list]: Save destination starting with'/'. ('/' から始まる保存先)
        upload_file[list]: Save file. You can start with a folder, but the file is placed directly under upload_path in the save hierarchy. (保存ファイル。フォルダなどから始まっても良いが、保存階層はupload_pathの直下にファイルが置かれる。)
        make_new_path[bool]: Whether to create if there is no path to the save destination. (保存先までのpathがない場合作成するかどうか)
        '''

        if len(upload_path) != len(upload_file):
            assert False, 'Uploading is not possible because there is no path to the save destination.\n保存先までのパスがないためアップロードできません。' 
        tmp_memory = 'None'
        for i in range(len(upload_path)):
            if tmp_memory != f"/{upload_path[i].split('/')[1]}":
                tmp_memory = f"/{upload_path[i].split('/')[1]}"
                if not self.__check_up_path(tmp_memory): # Check if there is a save destination path. (保存先のpathがあるかどうかを調べる)
                    if make_new_path: self.make_folder(upload_path[i])
                    else : assert False, 'Uploading is not possible because there is no path to the save destination.\n保存先までのパスがないためアップロードできません。'

            db_upload_file = upload_file[i].split('/')[-1] 
            #self.get_files(upload_path[i], 'file', recursive = True, save = False, reset = False, output = False)
            if f'{upload_path[i]}/{db_upload_file}' in [entry.path_display for entry in self.entry_list]:
                if skip :
                    print(f'{db_upload_file} は既に存在しているのでスキップします。')
                    continue
                assert overwrite, 'The file already exists. To overwrite, set "overwrite = True".\n既にファイルが存在します。上書きする場合は"overwrite = True"にしてください。' 

            try :
                with open(upload_file[i], "rb") as f: 
                    file_size = os.path.getsize(upload_file[i]) 
                    print(f'{db_upload_file} : {file_size} byte')
                    chunk_size = 100 * 1024 * 1024
                    if file_size <= chunk_size: self.__upload_file(upload_path[i], upload_file[i]) 
                    else: 
                        with tqdm(total=file_size, desc="Uploaded") as pbar: 
                            upload_session_start_result = self.dbx.files_upload_session_start(f.read(chunk_size))
                            pbar.update(chunk_size)
                            cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id, offset=f.tell())
                            commit = dropbox.files.CommitInfo(path=f'{upload_path[i]}/{db_upload_file}', mode=dropbox.files.WriteMode('overwrite'))
                            while f.tell() < file_size:
                                if (file_size - f.tell()) <= chunk_size: print(self.dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit))
                                else:
                                    self.dbx.files_upload_session_append(f.read(chunk_size), cursor.session_id, cursor.offset)
                                    cursor.offset = f.tell()
                                pbar.update(chunk_size)
            except Exception as e:
                print(f'{upload_path[i]}/{db_upload_file}は保存できません。')
                self.error_file_path.append(db_upload_file)

    # Check if there is a save destination path. (保存先のpathがあるかどうかを調べる)
    def __check_up_path(self, upload_path):
        try : self.get_files(upload_path, 'all', recursive = True, save = True, reset = False, output = False) # Get the path of the save destination recursively. (保存先のpathを再起的に取得する)
        except : return False
        else : return True

    # Create a folder. (フォルダ作成を行う)
    def make_folder(self, upload_path):
        split_upload_path = upload_path.split('/')
        for i in range(2, len(split_upload_path) + 1):
            if not self.__check_up_path('/'.join(split_upload_path[:i])): self.dbx.files_create_folder('/'.join(split_upload_path[:i]))
        
    # Upload the file. (ファイルのアップロードを行う)
    def __upload_file(self, upload_path, upload_file):
        db_upload_file = upload_file.split('/')[-1] 
        remote = f'{upload_path}/{db_upload_file}'
        with open(upload_file, 'rb') as f: self.dbx.files_upload(f.read(), remote, mode=dropbox.files.WriteMode('overwrite'))
        return True

    # Read file. (ファイルの読み込み) ------------------------------------------------------------------------------------------------------------
    
    # Read the file as a variable. (ファイルを変数として読み込む)
    def read_file(self, read_file_path):
        metadata, f = self.dbx.files_download(read_file_path)
        return metadata, f

    # Download and save the file. (ファイルをダウンロードして保存する)
    def download_file(self, read_file_path, save_path):
        try : self.dbx.files_download_to_file(save_path, read_file_path)
        except Exception as e : print(e)
        else : print('It was downloaded successfully.\n正常に保存されました。')