import boto
from boto.s3.key import Key
from boto.s3.connection import S3Connection
from boto.exception import S3ResponseError
import threading
import logging
import certifi, os

os.environ["SSL_CERT_FILE"] = certifi.where()


"""S3Thread

Upload File to a S3 bucket [capital-one-S3-bucket-name]
file_name: path to local file with the file name and extension
s3_folder_name: folder name on S3 bucket file saved to
s3_file_name: name the uploaded file on S3 bucket
"""

class S3FileExistError(Exception):
    def __init__(self, file):
        self.file = file
        self.message = (
            "File Name already exist in S3 bucket [capital-one-S3-bucket-name]"
        )
        super().__init__(self.message)

    def __str__(self):
        return f"{self.file} -> {self.message}"


class S3Thread(threading.Thread):
    def __init__(self, file_name, s3_folder_name, s3_file_name, on_success, on_error, 
                 aws_access_key, aws_secret_key):
        threading.Thread.__init__(self)
        self.file_name = file_name
        self.s3_file_name = s3_file_name
        self.s3_folder_name = s3_folder_name
        self.on_success = on_success
        self.on_error = on_error
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key

    def run(self):
        try:

            conn = S3Connection(
                self.aws_access_key, self.aws_secret_key
            )
            self.ow_tracking_bucket = conn.get_bucket("capital-one-S3-bucket-name")
            if self._isFileNameExist():
                print("file name exist on S3")
                raise S3FileExistError(self.s3_folder_name + "/" + self.s3_file_name)
                return
            k = Key(self.ow_tracking_bucket)
            k.key = self.s3_folder_name + "/" + self.s3_file_name

            k.set_contents_from_filename(self.file_name)
        except S3ResponseError as e:
            # This is a general exception when an error response is provided by an AWS service
            self.on_error(e) if self.on_error else None
            logging.error(e)  # remove if we want to handle all logging outside
            return
        except FileNotFoundError as e:
            # Local file does not exist
            self.on_error(e) if self.on_error else None
            logging.error(e)  # remove if we want to handle all logging outside
            return
        except S3FileExistError as e:
            # Custom error -> file already exist on S3 bucket
            self.on_error(e) if self.on_error else None
            logging.error(e)  # remove if we want to handle all logging outside
            return

        self.on_success(self.file_name) if self.on_success else None

    def _isFileNameExist(self):
        if self.ow_tracking_bucket.get_key(
            self.s3_folder_name + "/" + self.s3_file_name
        ):
            return True
        return False
