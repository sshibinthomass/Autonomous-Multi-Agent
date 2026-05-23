import React from 'react';

interface MarkdownProps {
  content: string;
}

interface Block {
  type: 'code' | 'header' | 'list' | 'blockquote' | 'paragraph';
  lang?: string;
  code?: string;
  level?: number;
  ordered?: boolean;
  items?: string[];
  text?: string;
}

const parseItalic = (text: string, parentIndex: number): React.ReactNode => {
  const italicRegex = /(\*.*?\*|_.*?_)/g;
  const parts = text.split(italicRegex);
  
  if (parts.length === 1) {
    return text;
  }
  
  return (
    <span key={parentIndex}>
      {parts.map((part, index) => {
        if ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) {
          return <em key={index}>{part.slice(1, -1)}</em>;
        }
        return part;
      })}
    </span>
  );
};

const renderInline = (text: string): React.ReactNode[] => {
  if (!text) return [];
  
  // Regex to match bold, inline code, and link patterns
  const inlineRegex = /(\*\*.*?\*\*|__.*?__|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  const parts = text.split(inlineRegex);
  
  return parts.map((part, index) => {
    if (!part) return null;
    
    // Bold: **text** or __text__
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    
    // Inline Code: `code`
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={index} className="inline-code">{part.slice(1, -1)}</code>;
    }
    
    // Link: [text](url)
    if (part.startsWith('[') && part.includes('](') && part.endsWith(')')) {
      const closingBracket = part.indexOf('](');
      if (closingBracket !== -1) {
        const linkText = part.substring(1, closingBracket);
        const linkUrl = part.substring(closingBracket + 2, part.length - 1);
        return (
          <a
            key={index}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="chat-link"
          >
            {linkText}
          </a>
        );
      }
    }
    
    // Fallback/Italic parsing
    return parseItalic(part, index);
  });
};

const parseNormalTextBlocks = (text: string): Block[] => {
  const blocks: Block[] = [];
  const lines = text.split('\n');
  
  let currentList: { ordered: boolean; items: string[] } | null = null;
  let currentBlockquote: string[] = [];
  let currentParagraph: string[] = [];
  
  const flushCurrent = () => {
    if (currentList) {
      blocks.push({
        type: 'list',
        ordered: currentList.ordered,
        items: currentList.items
      });
      currentList = null;
    }
    if (currentBlockquote.length > 0) {
      blocks.push({
        type: 'blockquote',
        text: currentBlockquote.join('\n')
      });
      currentBlockquote = [];
    }
    if (currentParagraph.length > 0) {
      const paragraphText = currentParagraph.join('\n').trim();
      if (paragraphText) {
        blocks.push({
          type: 'paragraph',
          text: paragraphText
        });
      }
      currentParagraph = [];
    }
  };
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    if (trimmedLine === '') {
      flushCurrent();
      continue;
    }
    
    // Headers (up to 6 levels)
    const headerMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headerMatch) {
      flushCurrent();
      blocks.push({
        type: 'header',
        level: headerMatch[1].length,
        text: headerMatch[2]
      });
      continue;
    }
    
    // Blockquotes
    const blockquoteMatch = line.match(/^>\s?(.*)$/);
    if (blockquoteMatch) {
      if (currentList || currentParagraph.length > 0) {
        flushCurrent();
      }
      currentBlockquote.push(blockquoteMatch[1]);
      continue;
    }
    
    // Unordered List Items
    const ulMatch = line.match(/^[-*]\s+(.*)$/);
    if (ulMatch) {
      if (currentList && currentList.ordered) {
        flushCurrent();
      }
      if (currentParagraph.length > 0 || currentBlockquote.length > 0) {
        flushCurrent();
      }
      if (!currentList) {
        currentList = { ordered: false, items: [] };
      }
      currentList.items.push(ulMatch[1]);
      continue;
    }
    
    // Ordered List Items
    const olMatch = line.match(/^(\d+)\.\s+(.*)$/);
    if (olMatch) {
      if (currentList && !currentList.ordered) {
        flushCurrent();
      }
      if (currentParagraph.length > 0 || currentBlockquote.length > 0) {
        flushCurrent();
      }
      if (!currentList) {
        currentList = { ordered: true, items: [] };
      }
      currentList.items.push(olMatch[2]);
      continue;
    }
    
    // Regular text line
    if (currentList || currentBlockquote.length > 0) {
      flushCurrent();
    }
    currentParagraph.push(line);
  }
  
  flushCurrent();
  return blocks;
};

export const Markdown: React.FC<MarkdownProps> = ({ content }) => {
  if (!content) return null;
  
  // Split on ``` to identify code blocks vs regular text
  const parts = content.split(/```/g);
  const blocks: Block[] = [];
  
  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    if (i % 2 === 1) {
      // Code block
      const firstNewlineIndex = part.indexOf('\n');
      let lang = '';
      let code = part;
      if (firstNewlineIndex !== -1) {
        const possibleLang = part.substring(0, firstNewlineIndex).trim();
        if (possibleLang.length < 15 && !possibleLang.includes(' ')) {
          lang = possibleLang;
          code = part.substring(firstNewlineIndex + 1);
        }
      }
      // Remove trailing newline if it exists
      if (code.endsWith('\n')) {
        code = code.slice(0, -1);
      }
      blocks.push({
        type: 'code',
        lang: lang || 'text',
        code: code
      });
    } else {
      // Normal text
      if (part) {
        blocks.push(...parseNormalTextBlocks(part));
      }
    }
  }
  
  return (
    <div className="markdown-content">
      {blocks.map((block, index) => {
        switch (block.type) {
          case 'code':
            return (
              <div key={index} className="markdown-code-wrapper">
                {block.lang && block.lang !== 'text' && (
                  <div className="markdown-code-lang">{block.lang}</div>
                )}
                <pre className="markdown-pre">
                  <code>{block.code}</code>
                </pre>
              </div>
            );
          case 'header': {
            const Tag = `h${block.level}` as any;
            return (
              <Tag key={index} className={`markdown-h${block.level}`}>
                {renderInline(block.text || '')}
              </Tag>
            );
          }
          case 'list': {
            const Tag = block.ordered ? 'ol' : 'ul';
            return (
              <Tag key={index} className={block.ordered ? 'markdown-ol' : 'markdown-ul'}>
                {block.items?.map((item, i) => (
                  <li key={i} className="markdown-li">
                    {renderInline(item)}
                  </li>
                ))}
              </Tag>
            );
          }
          case 'blockquote':
            return (
              <blockquote key={index} className="markdown-blockquote">
                {renderInline(block.text || '')}
              </blockquote>
            );
          case 'paragraph':
            return (
              <p key={index} className="markdown-p">
                {block.text?.split('\n').map((line, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && <br />}
                    {renderInline(line)}
                  </React.Fragment>
                ))}
              </p>
            );
          default:
            return null;
        }
      })}
    </div>
  );
};
