"""Read-only stdio MCP search over synthetic lesson notes."""
import json, os, re, sys

def main():
    lessons = json.loads(open(os.environ['CALYX_HISTORY_NOTES'], encoding='utf-8').read())
    tool = {'name': 'search_historical_lessons', 'description': 'Search synthetic historical engineering lessons by lexical overlap.', 'inputSchema': {'type': 'object', 'properties': {'query': {'type': 'string'}, 'top_k': {'type': 'integer'}}, 'required': ['query']}, 'annotations': {'readOnlyHint': True, 'openWorldHint': False}}
    for line in sys.stdin:
        if not line.strip():
            continue
        req = json.loads(line)
        rid = req.get('id')
        method = req.get('method')
        if rid is None and method.startswith('notifications/'):
            continue
        if method in ('initialize', 'init'):
            result = {'protocolVersion': '2024-11-05', 'serverInfo': {'name': 'synthetic-history', 'version': '1'}, 'capabilities': {'tools': {}}}
        elif method == 'tools/list':
            result = {'tools': [tool]}
        elif method == 'tools/call':
            args = req.get('params', {}).get('arguments', {})
            words = set(re.findall('[a-zA-Z_][a-zA-Z0-9_]*|//|\\+|-|\\[|\\]', str(args.get('query', '')).lower()))
            limit = min(max(int(args.get('top_k', 5)), 1), 10)
            ranked = []
            for lesson in lessons:
                text = (lesson['code'] + ' ' + lesson['lesson']).lower()
                tokens = re.findall('[a-zA-Z_][a-zA-Z0-9_]*|//|\\+|-|\\[|\\]', text)
                ranked.append((sum((tokens.count(w) for w in words if len(w) >= 3 or w in {'//', '+', '-', '[', ']'})), lesson))
            ranked.sort(key=lambda x: (-x[0], x[1]['id']))
            result = {'content': [{'type': 'text', 'text': json.dumps({'matches': [{**l, 'lexical_score': s} for s, l in ranked[:limit]]})}]}
        elif method == 'ping':
            result = {}
        else:
            result = {'error': {'code': -32601, 'message': 'method not found'}}
        print(json.dumps({'jsonrpc': '2.0', 'id': rid, 'result': result}), flush=True)
if __name__ == '__main__':
    main()
