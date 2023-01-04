from flask import current_app
import html2text


# Creating convertor so that search index is not including the html tags
h = html2text.HTML2Text()
h.ignore_links=True
h.ignore_emphasis=True


def add_to_index(index, model):

    if not current_app.elasticsearch:
        return
    
    payload = {}

    for field in model.__searchable__:
        payload[field] = getattr(model, field)

        if payload[field]:
            payload[field] = h.handle(payload[field])
    
    current_app.elasticsearch.index(index=index, doc_type=index, id=model.id,
                                    body=payload)
    

def remove_from_index(index, model):

    if not current_app.elasticsearch:
        return
    
    current_app.elasticsearch.delete(index=index, doc_type=index, id=model.id)


def query_index(index, query, page, per_page):

    if not current_app.elasticsearch:
        return [], [], 0

    search = current_app.elasticsearch.search(
        index=index, doc_type=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
        'from': (page - 1) * per_page, 'size': per_page})

    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    scores = [hit['_score'] for hit in search['hits']['hits']]

    return ids, scores, search['hits']['total']['value']
