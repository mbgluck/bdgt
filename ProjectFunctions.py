import psycopg2
import psycopg2.extras

# eventually get rid of these 2:
def return_query(query, cursor):
    cursor.execute(query)
    return cursor.fetchall()

def modify_query(conn, query):
    """ Execute a single INSERT request """
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1
    cursor.close()




def read_query(query, conn, var=()):
    """ Execute a single read request """
    cursor = conn.cursor()
    try:
        cursor.execute(query,var)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        cursor.close()
        raise psycopg2.DatabaseError
    
    return cursor.fetchall()
    cursor.close()

def write_query(query, conn, var=()):
    """ Execute a single write request """
    cursor = conn.cursor()
    try:
        cursor.execute(query,var)
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        raise psycopg2.DatabaseError
    cursor.close()

def write_return_query(query, conn, var=()):
    """ Execute a single write request with RETURNING, returns value """
    cursor = conn.cursor()
    try:
        cursor.execute(query, var)
        r = cursor.fetchone()[0]
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        raise psycopg2.DatabaseError
    cursor.close()
    return r

def set_field(conn, table, field, new_value, where):
    """set a field in a table. where clause is a list of 2 tuples (field, value)"""
    # stg_id = 234 and batch_id = 24
    # takes the first value in each tuple in pair and joins them with " and "
    w = ' and '.join(pair[0] + ' = %s' for pair in where)
    where_clause = 'where ' + w
    q = f"update {table} set {field} = %s" + where_clause
    v = ([new_value] + [pair[1] for pair in where])
    write_query(q, conn, v)
    msgw = where_clause % tuple(v[1:])
    print(f"{table} table updated {field} to {new_value} {msgw}")