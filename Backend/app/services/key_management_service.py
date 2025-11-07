from cryptography.fernet import Fernet 
from pymongo.database import Database
from app.db.key import insert_dek, get_dek, get_api_services, delete_api_key
import os, base64

class KMS:
    def __init__(self, KEK: str):
        self.f = Fernet(KEK)
    
    def encrypt_and_store(self,userid: str, service_name: str, api_key:str, mongo_db: Database): 
        DEK = Fernet.generate_key()
        fernet_dek = Fernet(DEK)
        encrypted_api_key = fernet_dek.encrypt(api_key.encode())
        encrypted_dek = self.f.encrypt(DEK) 

        key_dict = {"userid": userid, "dek": encrypted_dek,"service_name": service_name}
        generated = insert_dek(key_dict,mongo_db)
        return generated,encrypted_api_key  

    def decrypt_api_key(self,encrypted_api_key:str, userid:str, service_name:str, mongo_db: Database):
        encrypted_DEK = get_dek(service_name,userid,mongo_db)
        DEK = self.f.decrypt(encrypted_DEK).decode()
        fernet_dek = Fernet(DEK)
        api_key = fernet_dek.decrypt(encrypted_api_key).decode()
        return api_key 

    def get_api_services(self, userid: str, mongo_db:Database):
        api_services = get_api_services(userid,mongo_db)
        return api_services if api_services else None 

    def delete_api_key(self, userid: str, service_name: str, mongo_db:Database):
        return delete_api_key(userid, service_name, mongo_db)

    def generate_dsc_key(self, nbytes: int = 32) -> str:
        '''generate double submit cookie pattern key
        transport‑safe token.'''
        return base64.urlsafe_b64encode(os.urandom(nbytes)).decode().rstrip('=')        

