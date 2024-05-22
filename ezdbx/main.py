import os
import dropbox
import requests
import joblib
from tqdm import tqdm
from datetime import datetime
import zipfile

# Issuance of access token. (アクセストークンの発行)
def issue_access_token(APP_KEY, APP_SECRET):
    """
    発行したアクセストークンを返します。
    :param APP_KEY: Dropbox APIのアプリキー
    :param APP_SECRET: Dropbox APIのアプリシークレット
    :return: アクセストークン
    """
    print(f'https://www.dropbox.com/oauth2/authorize?client_id={APP_KEY}&response_type=code')
    AUTHORIZATION_CODE = input('AUTHORIZATION_CODE : ')
    data = {'code': AUTHORIZATION_CODE, 'grant_type': 'authorization_code'}
    response = requests.post('https://api.dropbox.com/oauth2/token', data=data, auth=(APP_KEY, APP_SECRET))
    DROPBOX_ACCESS_TOKEN = response.json()['access_token']
    return DROPBOX_ACCESS_TOKEN

# 更新トークンファイルの生成
def create_refresh_access_token_file(APP_KEY, APP_SECRET, save_file_path):
    """
    更新トークンファイルを生成します。
    :param APP_KEY: Dropbox APIのアプリキー
    :param APP_SECRET: Dropbox APIのアプリシークレット
    :param save_file_path: 保存するファイルパス
    """
    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
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
    """
    更新トークンファイルからアクセスキーを更新して取得します。
    :param load_path: 更新トークンファイルのパス
    :return: 更新されたアクセストークン
    """
    rdbx = joblib.load(load_path)
    rdbx.refresh_access_token()
    joblib.dump(rdbx, load_path, compress=3)
    print(f'update {load_path} success!')
    return rdbx._oauth2_access_token

class EzDbx:
    def __init__(self, DROPBOX_ACCESS_TOKEN):
        """
        クラスの初期化
        :param DROPBOX_ACCESS_TOKEN: Dropboxのアクセストークン
        """
        self.dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN, timeout=300)
        self.entry_list = []
        self.current_path = '/'
        self.cant_save_files = []
        self.output = True
    
    def ls(self, file_or_folder='all'):
        """
        現在のパスのファイルやフォルダをリスト表示します。
        :param file_or_folder: 'file', 'folder', 'all'のいずれかを指定
        """
        self.entry_list = self._get_entries(self.current_path, file_or_folder, recursive=False)
        print(f'current path : {self.current_path}')
        print(self.visible_path(current=True))

    def cd(self, change_directory='/'):
        """
        ディレクトリを変更します。
        :param change_directory: 移動するディレクトリパス
        :return: 現在のパス
        """
        if change_directory == '/':
            self.current_path = '/'
        elif change_directory == '..':
            self.current_path = '/'.join(self.current_path.split('/')[:-1]) or '/'
        else:
            new_path = os.path.join(self.current_path, change_directory).replace('//', '/')
            if self._check_path_exists(new_path):
                self.current_path = new_path
            else:
                raise ValueError('There is no path. (パスがありません。)')
        return self.current_path
    
    def get_files(self, db_root_dir, file_or_folder='all', recursive=False):
        """
        指定されたディレクトリのファイルやフォルダを取得します。
        :param db_root_dir: ルートディレクトリ
        :param file_or_folder: 'file', 'folder', 'all'のいずれかを指定
        :param recursive: 再帰的に取得するかどうか
        :return: エントリのリスト
        """
        return self._get_entries(db_root_dir, file_or_folder, recursive)
    
    def visible_path(self, current=False):
        """
        エントリのパスを表示します。
        :param current: 現在のパスのみを表示するかどうか
        :return: パスのリスト
        """
        return [entry.path_display.split('/')[-1] if current else entry.path_display for entry in self.entry_list]

    def get_shared_link(self, path):
        """
        指定されたパスの共有リンクを取得します。
        :param path: ファイルまたはフォルダのパス
        :return: 共有リンクのURL
        """
        links = self.dbx.sharing_list_shared_links(path=path, direct_only=True).links
        return links[0].url if links else self._create_shared_link(path)

    def upload(self, upload_file, upload_path='/', overwrite=False, skip=False, use_full_path=False):
        """
        ファイルをアップロードします。
        :param upload_file: アップロードするファイルのパス
        :param upload_path: アップロード先のパス
        :param overwrite: 上書きするかどうか
        :param skip: 既に存在するファイルをスキップするかどうか
        :param use_full_path: フルパスを使用するかどうか
        """
        if upload_path == '/':
            upload_path = self.current_path
        else:
            upload_path = os.path.join(self.current_path, upload_path).replace('//', '/')
        
        if use_full_path:
            db_upload_path = os.path.join(upload_path, upload_file.replace(os.sep, '/'))
        else:
            db_upload_path = os.path.join(upload_path, os.path.basename(upload_file))
        
        if self._check_file_exists(db_upload_path):
            if skip:
                print(f'{upload_file} は既に存在しているのでスキップします。')
                return
            elif not overwrite:
                raise ValueError('The file already exists. To overwrite, set "overwrite = True".\n既にファイルが存在します。上書きする場合は"overwrite = True"にしてください。')

        self._upload_file(upload_file, upload_path, use_full_path)

    def mkdir(self, upload_path):
        """
        フォルダを作成します。
        :param upload_path: 作成するフォルダのパス
        """
        path_parts = os.path.join(self.current_path, upload_path).replace('//', '/').split('/')
        for i in range(2, len(path_parts) + 1):
            dir_path = '/'.join(path_parts[:i])
            if not self._check_path_exists(dir_path):
                self.dbx.files_create_folder_v2(dir_path)

    def read_file(self, read_file_path):
        """
        ファイルを読み込みます。
        :param read_file_path: 読み込むファイルのパス
        :return: ファイルのデータ
        """
        return self.dbx.files_download(read_file_path)

    def download_file(self, read_file_path, save_path):
        """
        ファイルをダウンロードします。
        :param read_file_path: ダウンロードするファイルのパス
        :param save_path: 保存先のパス
        """
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            self.dbx.files_download_to_file(save_path, read_file_path)
            print(f'{read_file_path} was downloaded successfully.\n正常に保存されました。')
        except Exception as e:
            print(e)

    def write_sync(self, local_folder, dropbox_folder):
        """
        ローカルフォルダの内容をDropboxフォルダに同期します。
        :param local_folder: ローカルフォルダのパス
        :param dropbox_folder: Dropboxフォルダのパス
        """
        if not self._check_path_exists(dropbox_folder):
            self.mkdir(dropbox_folder)

        local_files = self._list_local_files(local_folder)
        dropbox_files, dropbox_folders = self._list_dropbox_files_and_folders(dropbox_folder, 'file')

        for local_file in local_files:
            relative_path = os.path.relpath(local_file, local_folder)
            dropbox_path = os.path.join(dropbox_folder, relative_path).replace(os.sep, '/')

            try:
                local_mod_time = datetime.fromtimestamp(os.path.getmtime(local_file))
            except OSError:
                local_mod_time = None

            if dropbox_path in dropbox_files:
                dropbox_mod_time = dropbox_files[dropbox_path]
                if abs((local_mod_time - dropbox_mod_time).total_seconds()) < 2:
                    print(f'Local file and Dropbox file are identical: {local_file}')
                elif local_mod_time > dropbox_mod_time:
                    self.upload(local_file, os.path.dirname(dropbox_path), overwrite=True)
            else:
                if local_mod_time is None:
                    self._handle_unsupported_file(local_file, dropbox_path)
                else:
                    self.upload(local_file, os.path.dirname(dropbox_path), overwrite=True)

    def read_sync(self, local_folder, dropbox_folder):
        """
        Dropboxフォルダの内容をローカルフォルダに同期します。
        :param local_folder: ローカルフォルダのパス
        :param dropbox_folder: Dropboxフォルダのパス
        """
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)

        dropbox_files, dropbox_folders = self._list_dropbox_files_and_folders(dropbox_folder, 'all')

        # ファイルのダウンロード
        for dropbox_path, dropbox_mod_time in dropbox_files.items():
            relative_path = os.path.relpath(dropbox_path, dropbox_folder)
            local_path = os.path.join(local_folder, relative_path)
            local_path = os.path.normpath(local_path)
            
            if not os.path.exists(local_path):
                self.download_file(dropbox_path, local_path)
            else:
                local_mod_time = datetime.fromtimestamp(os.path.getmtime(local_path))
                if local_mod_time < dropbox_mod_time:
                    self.download_file(dropbox_path, local_path)

    def cleanup_local_files(self, local_folder, dropbox_folder):
        """
        ローカルフォルダの内容をチェックし、Dropboxに存在する場合はローカルから削除します。
        また、空のフォルダも削除します。
        :param local_folder: ローカルフォルダのパス
        :param dropbox_folder: Dropboxフォルダのパス
        """
        # ローカルファイルリストの取得
        local_files = self._list_local_files(local_folder)
        
        # Dropbox内のファイルリストの取得
        dropbox_files, _ = self._list_dropbox_files_and_folders(dropbox_folder, 'file')

        # ローカルファイルリストとDropboxファイルリストの差分を取得し、ファイルを削除
        for local_file in local_files:
            relative_path = os.path.relpath(local_file, local_folder)
            dropbox_path = os.path.join(dropbox_folder, relative_path).replace(os.sep, '/')
            
            if dropbox_path in dropbox_files:
                try:
                    if os.path.isfile(local_file):
                        os.remove(local_file)
                        print(f'{local_file} was successfully deleted from local storage.')
                except Exception as e:
                    print(f'Error deleting {local_file}: {e}')

        # 空のフォルダを再帰的に削除
        self._remove_empty_dirs(local_folder)

    def check_exists(self, file_path):
        """
        指定したファイルまたはフォルダが存在するかを確認します。
        :param file_path: ファイルまたはフォルダのパス
        :return: 存在する場合はTrue、存在しない場合はFalse
        """
        return self._check_file_exists(file_path)
    
    def delete_file_or_folder(self, path):
        """
        指定したファイルまたはフォルダを削除します。
        :param path: 削除するファイルまたはフォルダのパス
        """
        try:
            self.dbx.files_delete_v2(path)
            print(f'{path} was deleted successfully.')
        except dropbox.exceptions.ApiError as e:
            print(f'Error deleting {path}: {e}')

    def move_file_or_folder(self, from_path, to_path):
        """
        指定したファイルまたはフォルダを移動します。
        :param from_path: 移動元のパス
        :param to_path: 移動先のパス
        """
        try:
            self.dbx.files_move_v2(from_path, to_path)
            print(f'{from_path} was moved to {to_path} successfully.')
        except dropbox.exceptions.ApiError as e:
            print(f'Error moving {from_path} to {to_path}: {e}')

    def copy_file_or_folder(self, from_path, to_path):
        """
        指定したファイルまたはフォルダをコピーします。
        :param from_path: コピー元のパス
        :param to_path: コピー先のパス
        """
        try:
            self.dbx.files_copy_v2(from_path, to_path)
            print(f'{from_path} was copied to {to_path} successfully.')
        except dropbox.exceptions.ApiError as e:
            print(f'Error copying {from_path} to {to_path}: {e}')

    def get_file_metadata(self, path):
        """
        指定したファイルまたはフォルダのメタデータを取得します。
        :param path: ファイルまたはフォルダのパス
        :return: メタデータ
        """
        try:
            metadata = self.dbx.files_get_metadata(path)
            print(f'Metadata for {path}: {metadata}')
            return metadata
        except dropbox.exceptions.ApiError as e:
            print(f'Error getting metadata for {path}: {e}')
            return None

    def list_folder_recursive(self, folder):
        """
        指定したフォルダ内のファイルやフォルダを再帰的にリストします。
        :param folder: フォルダのパス
        """
        entries = self._get_entries(folder, 'all', recursive=True)
        for entry in entries:
            print(entry.path_display)

    def cant_savefile(self):
        """
        保存できなかったファイルのリストを返します。
        :return: 保存できなかったファイルのリスト
        """
        return self.cant_save_files
    
    def _remove_empty_dirs(self, root_dir):
        """
        指定されたフォルダ内を探索し、最も深い階層から空のフォルダを再帰的に削除するメソッド。
        :param root_dir: ルートディレクトリのパス
        """
        # ディレクトリ内の全ての項目をリスト
        items = os.listdir(root_dir)
        
        # 各項目をチェック
        for item in items:
            item_path = os.path.join(root_dir, item)
            # 項目がディレクトリの場合、再帰的に呼び出し
            if os.path.isdir(item_path):
                self._remove_empty_dirs(item_path)
        
        # フォルダが空であれば削除
        try:
            if not os.listdir(root_dir):
                os.rmdir(root_dir)
                print(f'削除されたフォルダ: {root_dir}')
        except Exception as e:
            print(f'Error deleting folder {root_dir}: {e}')

    def _list_local_files(self, folder):
        """
        ローカルフォルダ内のファイルをリストします。
        :param folder: フォルダのパス
        :return: ファイルのリスト
        """
        file_list = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_list.append(os.path.join(root, file))
        return file_list
    
    def _list_dropbox_files_and_folders(self, folder, status):
        """
        Dropboxフォルダ内のファイルとフォルダをリストします。
        :param folder: フォルダのパス
        :param status: 'file', 'folder', 'all'のいずれかを指定
        :return: ファイルとフォルダのリスト
        """
        dropbox_files = {}
        dropbox_folders = set()
        self._get_entries(folder, status, recursive=True)
        for entry in self.entry_list:
            if isinstance(entry, dropbox.files.FileMetadata):
                dropbox_files[entry.path_display] = entry.client_modified
            elif isinstance(entry, dropbox.files.FolderMetadata):
                dropbox_folders.add(entry.path_display)
        return dropbox_files, dropbox_folders
    
    def _get_entries(self, path, file_or_folder, recursive):
        """
        指定したパスのエントリを取得します。
        :param path: パス
        :param file_or_folder: 'file', 'folder', 'all'のいずれかを指定
        :param recursive: 再帰的に取得するかどうか
        :return: エントリのリスト
        """
        self.entry_list = []
        try:
            res = self.dbx.files_list_folder(path, recursive=recursive, limit=2000)
            self.entry_list.extend(self._filter_entries(res.entries, file_or_folder))
            while res.has_more:
                res = self.dbx.files_list_folder_continue(res.cursor)
                self.entry_list.extend(self._filter_entries(res.entries, file_or_folder))
        except dropbox.exceptions.ApiError:
            raise ValueError('There is no path. (パスがありません。)')
    
    def _filter_entries(self, entries, file_or_folder):
        """
        エントリをフィルタリングします。
        :param entries: エントリのリスト
        :param file_or_folder: 'file', 'folder', 'all'のいずれかを指定
        :return: フィルタリングされたエントリのリスト
        """
        if file_or_folder == 'file':
            return [entry for entry in entries if isinstance(entry, dropbox.files.FileMetadata)]
        elif file_or_folder == 'folder':
            return [entry for entry in entries if not isinstance(entry, dropbox.files.FileMetadata)]
        elif file_or_folder == 'all':
            return entries
        else:
            raise ValueError('Invalid argument. Available values are "file", "folder", "all".')

    def _check_path_exists(self, path):
        """
        指定したパスが存在するかどうかを確認します。
        :param path: パス
        :return: 存在する場合はTrue、存在しない場合はFalse
        """
        try:
            self.dbx.files_get_metadata(path)
            return True
        except dropbox.exceptions.ApiError:
            return False

    def _check_file_exists(self, file_path):
        """
        指定したファイルが存在するかどうかを確認します。
        :param file_path: ファイルのパス
        :return: 存在する場合はTrue、存在しない場合はFalse
        """
        return self._check_path_exists(file_path)

    def _create_shared_link(self, path):
        """
        指定したパスの共有リンクを作成します。
        :param path: パス
        :return: 共有リンクのURL
        """
        setting = dropbox.sharing.SharedLinkSettings(requested_visibility=dropbox.sharing.RequestedVisibility.public)
        link = self.dbx.sharing_create_shared_link_with_settings(path=path, settings=setting)
        return link.url

    def _upload_file(self, upload_file, upload_path, use_full_path):
        """
        ファイルをアップロードします。
        :param upload_file: アップロードするファイルのパス
        :param upload_path: アップロード先のパス
        :param use_full_path: フルパスを使用するかどうか
        """
        try:
            with open(upload_file, "rb") as f:
                file_size = os.path.getsize(upload_file)
                print(f'{upload_file} : {file_size} byte')
                chunk_size = 100 * 1024 * 1024
                if file_size <= chunk_size:
                    if use_full_path:
                        db_upload_path = os.path.join(upload_path, upload_file.replace(os.sep, '/'))
                    else:
                        db_upload_path = os.path.join(upload_path, os.path.basename(upload_file))
                    self.dbx.files_upload(f.read(), db_upload_path, mode=dropbox.files.WriteMode('overwrite'))
                else:
                    with tqdm(total=file_size, desc="Uploaded") as pbar:
                        upload_session_start_result = self.dbx.files_upload_session_start(f.read(chunk_size))
                        pbar.update(chunk_size)
                        cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id, offset=f.tell())
                        commit = dropbox.files.CommitInfo(path=os.path.join(upload_path, os.path.basename(upload_file)), mode=dropbox.files.WriteMode('overwrite'))
                        while f.tell() < file_size:
                            if (file_size - f.tell()) <= chunk_size:
                                self.dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit)
                            else:
                                self.dbx.files_upload_session_append(f.read(chunk_size), cursor.session_id, cursor.offset)
                                cursor.offset = f.tell()
                            pbar.update(chunk_size)
        except OSError as e:
            print(f'Error uploading file {upload_file}: {e}')
            self._handle_unsupported_file(upload_file, os.path.join(upload_path, os.path.basename(upload_file)))

                        
    def _handle_unsupported_file(self, local_file, dropbox_path):
        try : 
            zip_path = local_file + '.zip'
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                zipf.write(local_file, os.path.basename(local_file))
            self.upload(zip_path, os.path.dirname(dropbox_path), overwrite=True)
            os.remove(zip_path)
        except Exception as e:
            print(f'{local_file} は保存できませんでした。保存できなかったファイルを確認する場合は cant_savefile メソッドを参照してください。')
            self.cant_save_files.append(local_file)