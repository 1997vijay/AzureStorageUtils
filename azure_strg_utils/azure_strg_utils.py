"""
Azure Storage Utils to interect with azure storage services

Dependencies:
    - pandas: Data manipulation and analysis library
    - azure-storage-blob: Azure python sdk to intrect with azure storage services

Usage:
    1. Ensure that you have the required dependencies installed.
    2. Set up your azure storage connection string or provide them through other means (e.g., environment variables).
    3. Run the code to intrect with azure storage.
    4. Below are the activity that we can perform on storage account
        1. Create container
        2. List Containers
        3. List Blobs
        4. Download single file or specific file or entire blob
        5. Upload single or specific file
        6. Delete single or specific file from blob
        7. Delete single or all containers
        8. Copy from one container to another container in the same storage account.
        9. Download or Delete based on the date and condition like greater_than, less_than etc.
        10. We can apply file regex to download ,delete or upload files that have specific pattern



    Author Information:
    Name: Vijay Kumar
    Date: 8 Dec 2023

Abstract/Description:

This code can be used to intrect with azure storage. It can we used to perform various activity on storage account.


Change Log:
    - 8 Dec 2023: Initial creation.
    - [Date]: Updated with new data. -- Use this when updated 

"""

from azure.storage.blob import BlobServiceClient,BlobBlock
from datetime import datetime
from io import BytesIO

import os
import sys
import pandas as pd
import fnmatch
import uuid
import time
import operator

      
class AzureStorageUtils:
    def __init__(self,connection_string) -> None:
        """
        Initialize the object with Azure Storage connection string.
        Args:
            connection_string (str): Azure storage account connection string.
        """
        self.__connection_string=connection_string

        if self.__connection_string!='' or self.__connection_string is not None:
            try:
                self._client=BlobServiceClient.from_connection_string(conn_str=self.__connection_string)
            except Exception as e:
                raise e
        else:
            raise ValueError('Invalid connection string!!')

    def list_container(self):
        """
        Get the list of containers present in the storage account.
        Returns: List of containers.
        """

        try:
            containers = self._client.list_containers()
            containers_list=[container.name for container in containers]
            return containers_list
        except Exception as e:
            raise e
    
    def list_folders(self,container_name):
        """
        Get the list of blobs/folders present in a container.
        Returns:
            List of blobs/folders.
        """

        folder_list=[]
        try:
            container_client=self._client.get_container_client(container_name)
            blob=container_client.list_blobs()
            folder_list=[file.name.split('/')[0] for file in blob]
            return list(set(folder_list))
        except Exception as e:
            raise e
    
    def list_files(self,container_name,blob_name):
        """
        Get the list of blobs/folders present in a container.
        Returns:
            List of blobs/folders.
        """

        try:
            container_client=self._client.get_container_client(container=container_name)
            blob=container_client.list_blobs(name_starts_with=blob_name)
            files=[]
            for file in blob:
                file_name=file.name.replace(f"{blob_name}/",'')
                if file_name!='' and file_name!=blob_name:
                    files.append(file_name)
            return files
        except Exception as e:
            raise e
    
    def download_file(self,container_name,blob_name,file_name:str=None,path:str='download',is_dataframe:bool=False,all_files:bool=False,file_regex:str=None):
        """
        Download a file/all files from Azure Blob Storage.
        Args:
            container_name (str): Container name.
            blob_name (str): Blob name.
            file_name (str): File name to be downloaded.

        Kwargs:
            path (str, optional): Location where the file will be saved. Default is './download'.
            is_dataframe (bool, optional): Return a dataframe without downloading the file. Default is False.
            all_files (bool, optional): download all file present in a blob
            file_regex (str, optional): You can pass the regex expresion to filter the files
        """

        try:
            if not is_dataframe:
                full_path = os.path.join(os.getcwd(),f"{path}/{blob_name}")
                current_path=full_path
                if not os.path.exists(full_path):
                    os.makedirs(full_path)
            is_data=False
            if is_dataframe:
                blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file_name}")
                stream = BytesIO()
                blob_client.download_blob().download_to_stream(stream)
                stream.seek(0)

                name, extension = file_name.split('.')
                extension = extension.lower()

                if extension == 'csv':
                    df = pd.read_csv(stream)
                elif extension == 'xlsx':
                    df = pd.read_excel(stream)
                elif extension == 'json':
                    df = pd.read_json(stream)
                else:
                    raise ValueError(f"Unsupported file format: {extension}")
                return df
            
            elif all_files:
                file_list=self.list_files(container_name=container_name,blob_name=blob_name)
                file_list=self._filter_file(file_regex=file_regex,file_list=file_list)

                count=0
                for file in file_list:
                    current_path=full_path
                    is_data=False
                # Creating directories and moving files
                    if '/' in file:
                        if '.' not in file:
                            current_path = os.path.join(current_path, file)
                            if not os.path.exists(current_path):
                                os.makedirs(current_path)
                        else:
                            current_path = os.path.join(current_path, file)

                            blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file}")
                            try:
                                data=blob_client.download_blob().readall()
                                is_data=True
                            except Exception as e:
                                raise e
                            if is_data:
                                with open(current_path,"wb") as f:
                                    f.write(data)
                                    count=count+1

                    elif '.' not in file:
                        current_path = os.path.join(current_path, file)
                        if not os.path.exists(current_path):
                                os.makedirs(current_path)
                    else:

                        blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file}")
                        try:
                            data=blob_client.download_blob().readall()
                            is_data=True
                        except Exception as e:
                            raise e

                        if is_data:
                            with open(f"{full_path}/{file}","wb") as f:
                                f.write(data)
                                count=count+1
                print(f'{count} files downloaded from container: {container_name} successfully')
            else:
                if file_name and not isinstance(file_name, int) and file_name.strip():
                    try:
                        blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file_name}")
                        data=blob_client.download_blob().readall()
                        is_data=True
                    except Exception as e:
                        sys.exit(e)

                    if is_data:
                        with open(f"{full_path}/{file_name}","wb") as f:
                            f.write(data)
                            print(f'{file_name} downloaded from container: {container_name} successfully')
                else:
                    sys.exit('Invalid file name!!')
        except Exception as e:
            raise e
    
    def upload_file(self,container_name,blob_name,file_path,file_name:str=None,all_files:bool=False,file_regex:str=None):
        """
        Upload a file from a local directory to Azure Blob Storage.
        Args:
            container_name (str): Container name.
            blob_name (str): Blob name.
            file_path (str): Local file path.

        Kwargs:
            file_name (str, optional): File name. Default is None.
            all_files (bool, optional): If True, upload all files from the given directory. Default is False.
            file_regex (str, optional): You can pass the regex expresion to filter the files
        """
        full_path = os.path.join(os.getcwd(),file_path)
        try:
            if all_files:
                files=os.listdir(full_path)
                files=self._filter_file(file_regex=file_regex,file_list=files)
                print(f'Uploading {len(files)} files !!')

                flag=False
                count=0
                if len(files)==0:
                    sys.exit('Empty folder!!')
                else:
                    for file in files:
                        count=count+1
                        print(f'{count}/{len(files)} done.',end='\r')
                        file_stats = os.stat(file_path+'/'+file)
                        file_size=round(file_stats.st_size / (1024 * 1024),2)

                        blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file}")

                        # send large file in chunk of 100 MB
                        if file_size>200:
                                block_list=[]
                                chunk_size=1024*1024*100

                                with open(f"{file_path}/{file}","rb") as f:

                                    while True:
                                        read_data = f.read(chunk_size)
                                        if not read_data:
                                            break
                                        blk_id = str(uuid.uuid4())
                                        blob_client.stage_block(block_id=blk_id,data=read_data)
                                        block_list.append(BlobBlock(block_id=blk_id))
                                blob_client.commit_block_list(block_list)
                        else:
                            with open(f"{file_path}/{file}","rb") as f:
                                data=f.read()
                                result=blob_client.upload_blob(data,overwrite=True)
                                if result['request_id']:
                                    flag=True
                if flag:
                    print(f'{len(files)} files uploaded to container: {container_name} successfully')
                else:
                    print('Something went wrong!!')
            else:
                blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file_name}")
                with open(f"{full_path}/{file_name}","rb") as f:
                    data=f.read()
                    result=blob_client.upload_blob(data,overwrite=True)
                    if result['request_id']:
                        print(f'{file_name} uploaded to container: {container_name} successfully')

        except Exception as e:
            message=f'Error while uploading the file!!,{e}'
            sys.exit(message)
    
    def delete_file(self,container_name,blob_name,file_name:str=None,all_files:bool=False,file_regex:str=None):
        """
        Delete files from Azure Blob Storage.
        Args:
            container_name (str): Container name.
            blob_name (str): Blob name from which the file will be deleted.
            file_name (str): File name to be deleted.

        Kwargs:
            all_files (bool, optional): If True, delete all files from the given blob. Default is False.
            file_regex (str, optional): You can pass the regex expresion to filter the files
        """

        try:
            if all_files:
                file_list=self.list_files(container_name=container_name,blob_name=blob_name)
                file_list=self._filter_file(file_regex=file_regex,file_list=file_list)

                for file in file_list:
                    blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file}")
                    blob_client.delete_blob(delete_snapshots='include')

                print(f'{len(file_list)} files deleted from container: {container_name} successfully')
            else:
                blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file_name}")
                blob_client.delete_blob(delete_snapshots='include')
                print(f'{file_name} deleted from container: {container_name} successfully')
        except Exception as e:
            message=f'Error while deleting the file!!,{e}'
            sys.exit(message)

    def _comparison_operator(self, comparison):
            """
            Returns the comparison operator based on the provided comparison type.
            Args:
                comparison (str): The type of comparison operator required. Possible values are:
                                - 'less_than': Less than comparison operator (<).
                                - 'less_than_or_equal': Less than or equal to comparison operator (<=).
                                - 'greater_than': Greater than comparison operator (>).
                                - 'greater_than_or_equal': Greater than or equal to comparison operator (>=).
                                - Any other value will return an equal to comparison operator (==).
            Returns:
                function: The comparison operator function based on the specified comparison type.
            """
            if comparison == 'less_than':
                return operator.lt
            elif comparison == 'less_than_or_equal':
                return operator.le
            elif comparison == 'greater_than':
                return operator.gt
            elif comparison == 'greater_than_or_equal':
                return operator.ge
            else:
                return operator.eq
    
    def _conditional_filter(self, container_name, blob_name, creation_date, comparison='less_than', file_regex=None):
        """
        Filter files based on certain criteria for deletion from Azure Blob Storage.

        Args:
            container_name (str): Name of the container in Azure Blob Storage.
            blob_name (str): Blob name from which the files will be filtered.
            creation_date (str): Date for comparison in the format '%Y-%m-%d'.
            comparison (str, optional): The type of comparison for file filtering (default is 'less_than').
            file_regex (str, optional): The regex expression used to filter the files (default is None).

        Returns:
            list: A list of files filtered based on the specified criteria.

        Explanation:
        This method filters files in the Azure Blob Storage based on the specified criteria.
        It retrieves a list of files from the blob specified by 'blob_name' in the 'container_name'.
        Then, it compares the creation date of each file with the 'creation_date' using the specified comparison
        operator (default is 'less_than'), and collects the files that meet the criteria for deletion/download.
        If 'file_regex' is provided, it further filters the files using the regex pattern.
        Returns a list of files that satisfy the criteria.
        """
        try:
            if comparison not in ['less_than','less_than_or_equal','greater_than','greater_than_or_equal']:
                raise ValueError("Invalid comparison operator. Use any one of them ['less_than','less_than_or_equal','greater_than','greater_than_or_equal']")
            
            file_list = []
            creation_date = datetime.strptime(creation_date, '%Y-%m-%d').date()

            container_client = self._client.get_container_client(container=container_name)
            blob = container_client.list_blobs(name_starts_with=blob_name)
            comparison_operator = self._comparison_operator(comparison=comparison)

            # Collect files for deletion based on date criteria
            for file in blob:
                if comparison_operator(file.creation_time.date(), creation_date):
                    file_name = file.name.replace(f"{blob_name}/", '')
                    if file_name != '' and file_name != blob_name:
                        file_list.append(file_name)

            # Filter files by regex pattern if provided
            file_list = self._filter_file(file_regex=file_regex, file_list=file_list)
            return file_list
        except Exception as e:
            raise e
        
    def conditional_operation(self, container_name, blob_name, creation_date, comparison='less_than', file_regex=None,action='download',path='download'):
            """
            Perform conditional operations on files in Azure Blob Storage based on specified criteria.
            Args:
                container_name (str): The name of the container in Azure Blob Storage.
                blob_name (str): The specific blob name in the container.
                creation_date (str): The creation date as a string in 'YYYY-MM-DD' format.
                comparison (str, optional): The type of comparison operator for date-based deletion.
                                            Possible values: 'less_than', 'less_than_or_equal',
                                            'greater_than', 'greater_than_or_equal', or any other value
                                            (defaults to 'less_than').
                file_regex (str, optional): Regex pattern to filter files for deletion. Defaults to None.
                action (str, optional): The action to perform - 'delete' or 'download'. Defaults to 'download'.
                path (str, optional): The path to download files when action is set to 'download'. Defaults to 'download'.

            Raises:
                Exception: If an error occurs during file deletion or download, it raises an exception.

            Returns:
                None: Performs file deletion or downloads files based on the specified action.

            Example:
                # Delete files older than a specified date
                client.conditional_operation('my_container', 'folder/subfolder', '2023-01-01', comparison='less_than', action='delete')

                # Download files matching a pattern created after a specific date
                client.conditional_operation('my_container', 'folder/subfolder', '2023-06-01', comparison='greater_than', file_regex='*.txt', action='download', path='local_folder')
            """
            try:
                count=0
                file_list=self._conditional_filter(container_name, blob_name, creation_date, comparison, file_regex)
                
                if action=='delete':
                    for file in file_list:
                        blob_client = self._client.get_blob_client(container=container_name, blob=f"{blob_name}/{file}")
                        blob_client.delete_blob(delete_snapshots='include')
                    print(f'{len(file_list)} files deleted from container: {container_name} successfully')
                else:
                    full_path = os.path.join(os.getcwd(),f"{path}/{blob_name}")
                    if not os.path.exists(full_path):
                        os.makedirs(full_path)

                    for file in file_list:
                        blob_client=self._client.get_blob_client(container=container_name,blob=f"{blob_name}/{file}")
                        try:
                            data=blob_client.download_blob().readall()
                            is_data=True
                        except Exception as e:
                            raise e

                        if is_data:
                            with open(f"{full_path}/{file}","wb") as f:
                                f.write(data)
                                count=count+1
                print(f'{count} files downloaded from container: {container_name} successfully')

            except Exception as e:
                message = f'Error while deleting the file!!,{e}'
                sys.exit(message)
        

    def _filter_file(self,file_regex,file_list):
        """
        Filter the list of files based on the provided regex pattern.
        Args:
            file_regex (str): The regex expression used to filter the files.
            file_list (list): List of file names to be filtered.
        Returns:
            list: A filtered list of file names based on the regex pattern.
        """
        if file_regex!=None and not isinstance(file_regex, int):
            file_list = fnmatch.filter(file_list, file_regex)
        else:
            file_list=file_list
        return file_list
    
    def copy_blob(self,container_name,blob_name,destination_container,destination_blob,file_name:str=None,all_files:bool=False,file_regex:str=None,abort_after:int=100):
        """
        Copy files or specific file from one Azure Blob Storage container to another.
        
        Args:
            container_name (str): Source container name.
            blob_name (str): Source blob name or pattern to filter files.
            destination_container (str): Destination container name.
            destination_blob (str): Destination blob name.

        Kwargs:
            file_name (str, optional): Specific file name to copy. Default is None.
            all_files (bool, optional): If True, copy all files from the source blob. Default is False.
            file_regex (str, optional): Regex pattern to filter files for copying.
            abort_after (int, optional): Abort the copy after given time (in seconds). Default is 100 seconds.

        Raises:
            Exception: Raises an exception if an error occurs during the copying process.
        """
        try:
            file_list=self.list_files(container_name,blob_name)
            file_list=self._filter_file(file_regex,file_list)
            count=0

            if all_files:
                for file in file_list:
                    count=count+1
                    # source and destination client
                    source_blob_client=self._client.get_blob_client(container=container_name,blob=f'{blob_name}/{file}')
                    destination_blob_client=self._client.get_blob_client(container=destination_container,blob=f'{destination_blob}/{file}')

                    # copy file
                    destination_blob_client.start_copy_from_url(source_url=source_blob_client.url)
            else:
                count=count+1
                # source and destination client
                source_blob_client=self._client.get_blob_client(container=container_name,blob=f'{blob_name}/{file_name}')
                destination_blob_client=self._client.get_blob_client(container=destination_container,blob=f'{destination_blob}/{file_name}')

                # copy file
                destination_blob_client.start_copy_from_url(source_url=source_blob_client.url)
                if abort_after:
                    self._abort_copy(blob_client=destination_blob_client,abort_time=abort_after)

            print(f'{count} files copied from container: {container_name}/{blob_name} to {destination_container}/{destination_blob}')
        except Exception as e:
            raise e
        
    def _abort_copy(self,blob_client,abort_time):
        """
        Abort a copy operation for a blob client if it takes longer than a specified duration.
        Args:
            blob_client: Blob client object representing the blob to monitor.
            abort_time (int): Time duration (in seconds) to monitor the copy operation and abort if necessary.

        Raises:
            Exception: Raises an exception if an error occurs during the abort operation.
        """
        try:
            for i in range(abort_time):
                status=blob_client.get_blob_properties().copy.status
                print("Copy status: " + status)
                if status=='success':
                    break
                time.sleep(1)

            if status!='success':
                props=blob_client.get_blob_properties()
                print(props.copy.status)
                copy_id=props.copy.id

                # abort the copy
                blob_client.abort_copy(copy_id)
                props = blob_client.get_blob_properties()
                print(props.copy.status)

        except Exception as e:
            raise e

    def create_container(self,container_name):
        """
        Create a container in Azure Storage.
        Args:
            container_name (str): Name of the new container.
        """
        try:
            # create containers
            self._client.create_container(container_name)

            # list containers
            container_list=self.list_container()
            print(f'Available containers: {container_list}')
        except Exception as e:
            sys.exit(e)
    
    def delete_container(self,container_name:str=None,all_containers:bool=False):
        """
        Delete a container from Azure Storage.
        Args:
            container_name (str): Name of the container to be deleted.
        Kwargs:
            all_container (bool, optional): If True, delete all containers. Default is False.
        """

        try:
            if all_containers:
                containers=self.list_container()
                print(f'Deleting {len(containers)} containers')

                for container in containers:
                    container_client=self._client.get_container_client(container=container)
                    container_client.delete_container()
                    print(f'Container {container_name} deleted successfully!!')
            else:
                # delete container
                container_client=self._client.get_container_client(container=container_name)
                container_client.delete_container()
                print(f'Container {container_name} deleted successfully!!')

                # list containers
                container_list=self.list_container()
                print(f'Available containers: {container_list}')
        except Exception as e:
            sys.exit(e)