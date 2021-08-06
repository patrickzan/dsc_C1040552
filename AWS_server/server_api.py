import zipfile, os, json, shutil
from collections import deque
from .s3thread import S3Thread
from plyer import uniqueid
from random import randint
from datetime import datetime

"""
Assume you are using your mobile phone Capital One App to make transactions:
This module can be integrated into the App to send transaction records into 
an AWS S3 bucket. 
"""

class DataHandler:
    def __init__(self, server_api, auth, data_dir, aws_access_key, aws_secret_key, num_transactions_keep=100):
        self.server_api = server_api
        self.auth = auth
        self.data_dir = data_dir
        self.device_id = uniqueid.id
        # self.transactions_kept = deque()
        self.num_transactions_keep = num_transactions_keep
        self.record_file = os.path.join(self.data_dir, "sentrecord.log")
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        if os.path.exists(self.record_file):
            with open(self.record_file, "r") as f:
                records = json.load(f)
            self.transactions_sent = deque(records["sent"])
            self.transactions_to_send = deque(records["to_send"])
        else:
            self.transactions_sent = deque()
            self.transactions_to_send = deque()

    def add_dir(self, dir_path):
        self.transactions_to_send.append(dir_path)
        while (
            len(self.transactions_sent) + len(self.transactions_to_send) > self.num_transactions_keep
            and len(self.transactions_sent) > 0
        ):
            dir_to_remove = self.transactions_sent.popleft()
            self.remove_dir(dir_to_remove)
        self.update_records()

    def update_records(self):
        records = {}
        records["sent"] = list(self.transactions_sent)
        records["to_send"] = list(self.transactions_to_send)
        with open(self.record_file, "w") as f:
            json.dump(records, f)

    def send_left_to_cloud(self):
        while self.transactions_to_send:
            dir_path = self.transactions_to_send[0]
            self.send_dir_to_server(dir_path)
            print("[ServerAPI ] self.transactions_sent", self.transactions_sent)
            print("[ServerAPI ] self.transactions_to_send", self.transactions_to_send)

    def send_dir_to_server(self, dir_path, thred=64):
        if not os.path.exists(dir_path):
            print(f"{dir_path} does NOT exist!")
            return
        # if self.check_file_size(dir_path) < thred:
        #     self.data_discarded()
        #     return
        # print('00000000:', os.listdir(dir_path))
        zip_path = self.zip_dir(dir_path)
        self.send_file_to_server(zip_path)

    def send_file_to_server(self, fpath):
        s3_folder = self.auth["email"] + "-" + self.device_id
        s3_filename = os.path.basename(fpath)
        print(f"[ServerAPI ] sending {fpath}, {s3_folder}, {s3_filename}.")
        self.s3_thread = S3Thread(
            fpath,
            s3_folder,
            s3_filename,
            self.data_sent_success,
            self.data_sent_failure,
            self.aws_access_key,
            self.aws_secret_key
        )
        self.s3_thread.start()
        # self.s3_thread.join()

    def zip_dir(self, dir_path):
        # ziph is zipfile handle
        date = str(datetime.now().date())
        rnd = randint(100, 999)
        trial_dirname = os.path.basename(dir_path)
        dirname = os.path.dirname(dir_path)
        zip_path = os.path.join(
            dirname, date + "-" + trial_dirname + "-" + str(rnd) + ".zip"
        )
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    zipf.write(os.path.join(root, file), file)
        if os.path.exists(zip_path):
            print("[ServerAPI ] zip_path generated!")
        else:
            print("[ServerAPI ] Failed to generated zip_path!")
        return zip_path

    def data_discarded(self):
        dir_path = self.transactions_to_send[0]
        print(f"[ServerAPI ] {dir_path} discarded")
        self.transactions_to_send.popleft()
        self.update_records()

    def data_sent_success(self, zip_path):
        dir_path = self.transactions_to_send.popleft()
        self.transactions_sent.append(dir_path)
        print(f"[ServerAPI ] Successfully sent {dir_path}")
        self.update_records()
        os.remove(zip_path)

    def data_sent_failure(self):
        print(f"[ServerAPI ] Failed to send {self.transactions_to_send[0]}.")

    def check_file_size(self, fpath):
        # data size in Bytes
        fstat = os.stat(fpath)
        return fstat.st_size

    def remove_dir(self, dir_path):
        try:
            shutil.rmtree(dir_path)
        except OSError as e:
            print("Error: %s : %s" % (dir_path, e.strerror))
