from builtins import str
from builtins import object
import boto3
import hashlib 
from boto3.session import Session

class SimpleDBKeyInUseException(Exception):
    pass


class BaseSimpleDB(object):
    domain = "default_domain"
    region = 'us-west-2'
    
    def _parse_attrs(self, attributes):
        attrs = {}
        for item in attributes:
            attrs[item['Name']] = item['Value']
        return attrs 

class Record(BaseSimpleDB):
    """ 
    Simple DB Record 
    Pass in a domain otherwise default_domain will be used.
    Usage:
    rec = Record(domain="mydomain")

    rec.key = "mykey"
    attrs = rec.fetch()

    attrs['new_attr'] = "new_val"
    rec.set_attributes(attrs)
    rec.update()

    """
    attributes = []
    key = None
    def __init__(self, **kwargs):
        for k in kwargs:
            if k == 'attributes':
                self.set_attributes(kwargs[k])
            else:
                setattr(self, k, kwargs[k])

        if hasattr(self, 'profile_name'):
            session = Session(profile_name=self.profile_name)
            self.conn = session.client('sdb', region_name=self.region)
        else:
            self.conn = boto3.client('sdb', region_name=self.region)




    def set_attributes(self, attrs, replace=True):
        if replace:
            self.attributes = []
        for name, value in attrs.items():
            self.add_attr(name, value, replace)

    def add_attr(self, name, value, replace=True):
        self.attributes.append({
            'Name': name,
            'Value': str(value),
            'Replace': replace
            })

    def get_attr(self, name):
        for x in self.attributes:
            if x['Name'] == name:
                return x['Value']


    def update(self):
        if not self.key:
            raise Exception("No key set")
        if not self.attributes:
            return False
        
        self.conn.put_attributes(
            DomainName=self.domain,
            ItemName=self.key,
            Attributes=self.attributes
            )

    def delete(self, key=None):
        if key:
            self.key=key
        if not self.key:
            raise Exception("No key set")

        response = self.conn.delete_attributes(
            DomainName=self.domain,
            ItemName=self.key,
                )


        
    def fetch(self, key=None):
        if key:
            self.key=key
        if not self.key:
            raise Exception("No key set")
        response = self.conn.get_attributes(
                DomainName=self.domain,
                ItemName=self.key,
                ConsistentRead=True
                )
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            self.attributes = response.get("Attributes", [])
            return self._parse_attrs(self.attributes)
        else:
            return None

    @classmethod
    def _make_key(cls, *argv, **opts):
        m = None
        if 'sha256' in opts and opts['sha256']:
            m = hashlib.sha256()
        else:
            m = hashlib.md5()

        for i, arg in enumerate(argv):
            #print i, arg
            m.update(str(arg).encode('utf-8'))
        return m.hexdigest()
        

    def make_key(self, *argv, **opts):
        """ 
        Use to make unique key for SimpleDB for both 
        Experiments and Experiments Participants
        m = hashlib.md5()
        for arg in argv:
            m.update(str(arg))
        key = m.hexdigest()
        """

        key = self._make_key(*argv, **opts)
        #print key
        check_record = Record(region=self.region, domain=self.domain, key=key)
        if check_record.fetch():
            raise SimpleDBKeyInUseException(key)
        self.key = key
        return self.key

     
class QuerySelect(BaseSimpleDB):
    """ 
    Convenience Class to make SQL queries on SimpleDB
    """
    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])
            

        if hasattr(self, 'profile_name'):
            session = Session(profile_name=self.profile_name)
            self.conn = session.client('sdb', region_name=self.region)
        else:
            self.conn = boto3.client('sdb', region_name=self.region)


    def sql(self, sql, items=None, next_token=None):
        """
        @Params
        sql: SQL query string

        Returns array of results
        """
        if not items:
            items = []
        if next_token:
            response = self.conn.select(
                    SelectExpression=sql,
                    NextToken=next_token,
                    ConsistentRead=True
                    )
        else:
            response = self.conn.select(
                    SelectExpression=sql,
                    ConsistentRead=True
                    )

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            for item in response.get("Items", []):
                items.append( self._parse_attrs(item.get("Attributes", [])) )
        
        next_token = response.get("NextToken")

        if next_token:
            return self.sql(sql, items, next_token)
        else:
            return items

class Domain(QuerySelect):
    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

        if hasattr(self, 'profile_name'):
            session = Session(profile_name=self.profile_name)
            self.conn = session.client('sdb', region_name=self.region)
        else:
            self.conn = boto3.client('sdb', region_name=self.region)

        
    def create(self, domain=None):
        if domain:
            self.domain = domain
        if not self.domain:
            raise Exception("Domain name is not set")

        response = self.conn.create_domain(
                DomainName=self.domain
                )

    def delete(self, domain=None):
        if domain:
            self.domain = domain
        if not self.domain:
            raise Exception("Domain name is not set")

        response = self.conn.delete_domain(
                DomainName=self.domain
                )

    def list_domains(self, items=None, next_token=None):
        if not items:
            items = []
        if next_token:
            response = self.conn.list_domains(
                    NextToken=next_token,
                    )
        else:
            response = self.conn.list_domains()

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            items.extend( response.get("DomainNames", []) ) 
        
        next_token = response.get("NextToken")

        if next_token:
            self.list_domains(sql, items, next_token)
        else:
            return items

    def count(self, key=None, value=None):
        """Count number of Items in a Domain"""
        sql = "SELECT count(*) FROM {} ".format(self.domain) 
        if key:
            sql = "SELECT count(*) FROM {} WHERE {} = '{}' ".format(self.domain, key, value)
        response = self.conn.select(
                SelectExpression=sql,
                ConsistentRead=True
                )

        return int( response.get('Items')[0]['Attributes'][0]['Value'] )

