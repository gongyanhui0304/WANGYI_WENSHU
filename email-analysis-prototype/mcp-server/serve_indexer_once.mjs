import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const filePath = resolve('email-analysis-prototype/mcp-server/server/mail_indexer.py');
const content = readFileSync(filePath);
const server = createServer((req, res) => {
  if (req.url === '/mail_indexer.py') {
    res.writeHead(200, { 'content-type': 'text/x-python; charset=utf-8', 'content-length': content.length });
    res.end(content);
    return;
  }
  res.writeHead(404, { 'content-type': 'text/plain' });
  res.end('not found');
});
server.listen(18765, '0.0.0.0', () => console.log('serving mail_indexer.py on 0.0.0.0:18765'));
