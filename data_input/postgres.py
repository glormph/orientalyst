import psycopg2, sys, logging 

log = logging.getLogger(__name__)

class DatabaseSession(object):
    def __init__(self, dbname, user):
        self.methods = {
                'insert' : self.insert,
                'upsert' : self.upsert,
        }
        self.conn = None
        try:
            self.conn = psycopg2.connect(database=dbname, user=user)
            print self.conn
        except Exception, e:
            raise
            self.error(e)

    def close(self):
        self.conn.close()

    def runsql(self, sql, data=None):
        self.cur = self.conn.cursor()
        try:
            if not data:
                self.cur.execute(sql)
            else:
                self.cur.execute(sql, data)
            self.conn.commit()
        except Exception, e:
            self.error(e)

    def runwrite(self, method, table, pk_fields=None, **kwargs):
        self.cur = self.conn.cursor()
        try:
            if pk_fields:
                rval = self.methods[method](self.cur, table, pk_fields, **kwargs)
            else:
                rval = self.methods[method](self.cur, table, **kwargs)
            self.conn.commit()
            return rval
        except:
            raise


    def error(self, e):
        if self.conn:
            self.conn.rollback()
            print 'ERRROR %s' % e            
            log.debug('Error ' )

    def select(self, cur, table, select_fields=None, **where_fields):
        if type(table) == list:
            table = ','.join(table)
        if not select_fields:
            select_fields = '*'
        elif type(select_fields) == list:
            select_fields = ', '.join(select_fields)

        where = []
        if where_fields is not {}:
            for f in where_fields:
                if where_fields[f] is not None:
                    where.append('{0}=%s'.format(f) )
                else:
                    where_fields[f] = None 
                    where.append('{0} IS %s'.format(f) )
            where = 'WHERE {0}'.format(' AND '.join(where) )
        else:
            where = ''

        where_args = [where_fields[x] for x in where_fields]
        cur.execute("SELECT {0} FROM {1} {2}".format(select_fields, table, where), where_args)


    def insert(self, cur, table, schema=None, **kwargs):
        if schema:
            rel = '{0}.{1}'.format(schema, table)
        else:
            rel = table

        fields = kwargs.keys()
        field_placeholders = ['%s'] * len(fields)
        values = [kwargs[f] for f in fields]
        cur.execute("INSERT INTO {0} ({1}) VALUES ({2})".format(rel, ','.join(fields), ', '.join(field_placeholders)), values)
        return True

    def upsert(self, cur, table, pk_fields, schema=None, **kwargs):
        assert len(pk_fields) > 0, 'At least one primary key field must be specififed'
        if schema:
            rel = '%s.%s' % (schema, table)
        else:
            rel = table        
        where = ' AND '.join('{0}=%s'.format(pkf) for pkf in pk_fields)
        where_args = [kwargs[pkf] for pkf in pk_fields]
        cur.execute('SELECT COUNT(*) FROM {0} WHERE {1} LIMIT 1'.format(rel,
            where), where_args)
        fields = [f for f in kwargs.keys()]
        if cur.fetchone()[0] > 0:
            set_clause = ', '.join('{0}=%s'.format(f) for f in fields if f not
                    in pk_fields)
            set_args = [kwargs[f] for f in fields if f not in pk_fields]
            cur.execute('UPDATE {0} SET {1} WHERE {2}'.format(rel, set_clause,
                where), set_args+where_args)
            return False
        else:
            self.insert(cur, table, schema, **kwargs) 
            return True 

    def fetchone(self, table, select_fields=None, **kwargs):
        cur = self.conn.cursor()
        self.select(cur, table, select_fields, **kwargs)
        return cur.fetchone()
    
    def fetchall(self, table, select_fields=None, **kwargs):
        cur = self.conn.cursor()
        self.select(cur, table, select_fields, **kwargs)
        return cur.fetchall()
    

    def update(self):
        pass

