import uuid, json
from esprit import raw, util

class StoreException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class DAO(object):
    
    @classmethod
    def makeid(cls):
        return uuid.uuid4().hex
    
    def actions(self, conn, action_queue):
        for action in action_queue:
            if action.keys()[0] == "remove":
                self._action_remove(conn, action)
            elif action.keys()[0] == "store":
                self._action_store(conn, action)
    
    def _action_remove(self, conn, remove_action):
        obj = remove_action.get("remove")
        if "index" not in obj:
            raise StoreException("no index provided for remove action")
        if "id" not in obj and "query" not in obj:
            raise StoreException("no id or query provided for remove action")
        if "id" in obj:
            raw.delete(conn, obj.get("index"), obj.get("id"))
        elif "query" in obj:
            raw.delete_by_query(conn, obj.get("index"), obj.get("query"))

    def _action_store(self, conn, store_action):
        obj = store_action.get("store")
        if "index" not in obj:
            raise StoreException("no index provided for store action")
        if "record" not in obj:
            raise StoreException("no record provided for store action")
        raw.store(conn, obj.get("index"), obj.get("record"), obj.get("id"))
    
class DomainObject(DAO):
    __type__ = None
    __conn__ = None
    
    def __init__(self, raw):
        self.data = raw
    
    @property
    def id(self):
        return self.data.get('id', None)
        
    @id.setter
    def id(self, val):
        self.data["id"] = val
    
    @property
    def json(self):
        return json.dumps(self.data)
    
    @property
    def raw(self):
        return self.data
    
    @classmethod
    def pull(cls, id_, conn=None):
        '''Retrieve object by id.'''
        if conn is None:
            conn = cls.__conn__
        
        if id_ is None:
            return None
        try:
            resp = raw.get(conn, cls.__type__, id_)
            if resp.status_code == 404:
                return None
            else:
                j = raw.unpack_get(resp)
                return cls(j)
        except:
            return None
    
    @classmethod
    def query(cls, q='', terms=None, facets=None, conn=None, **kwargs):
        '''Perform a query on backend.

        :param q: maps to query_string parameter if string, or query dict if dict.
        :param terms: dictionary of terms to filter on. values should be lists. 
        :param facets: dict of facets to return from the query.
        :param kwargs: any keyword args as per
            http://www.elasticsearch.org/guide/reference/api/search/uri-request.html
        '''
        if conn is None:
            conn = cls.__conn__
        
        if isinstance(q,dict):
            query = q
            if 'bool' not in query['query']:
                boolean = {'bool':{'must': [] }}
                boolean['bool']['must'].append( query['query'] )
                query['query'] = boolean
            if 'must' not in query['query']['bool']:
                query['query']['bool']['must'] = []
        elif q:
            query = {
                'query': {
                    'bool': {
                        'must': [
                            {'query_string': { 'query': q }}
                        ]
                    }
                }
            }
        else:
            query = {
                'query': {
                    'bool': {
                        'must': [
                            {'match_all': {}}
                        ]
                    }
                }
            }

        if facets:
            if 'facets' not in query:
                query['facets'] = {}
            for k, v in facets.items():
                query['facets'][k] = {"terms":v}

        if terms:
            boolean = {'must': [] }
            for term in terms:
                if not isinstance(terms[term],list): terms[term] = [terms[term]]
                for val in terms[term]:
                    obj = {'term': {}}
                    obj['term'][ term ] = val
                    boolean['must'].append(obj)
            if q and not isinstance(q,dict):
                boolean['must'].append( {'query_string': { 'query': q } } )
            elif q and 'query' in q:
                boolean['must'].append( query['query'] )
            query['query'] = {'bool': boolean}

        for k,v in kwargs.items():
            if k == '_from':
                query['from'] = v
            else:
                query[k] = v
        
        r = raw.search(conn, cls.__type__, query)
        # r = requests.post(cls.target() + recid + endpoint, data=json.dumps(query))
        return r.json()
    
    def save(self, conn=None, makeid=True, created=True, updated=True):
        if makeid:
            if "id" not in self.data:
                self.id = self.makeid()
        if created:
            if 'created_date' not in self.data:
                self.data['created_date'] = util.now()
        if updated:
            self.data['last_updated'] = util.now()
        
        if conn is None:
            conn = self.__conn__
        raw.store(conn, self.__type__, self.data, self.id)
        
    def delete(self, conn=None):
        if conn is None:
            conn = self.__conn__
        raw.delete(conn, self.__type__, self.id)
    
