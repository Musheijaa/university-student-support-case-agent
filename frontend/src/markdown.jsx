// Minimal, dependency-free renderer for the small subset of markdown the
// backend's prompts actually produce: **bold**, "- "/"1. " lists, and
// "|"-delimited tables. Not a general markdown parser - just enough to
// stop raw "**"/"|" characters showing up in the chat transcript.

function renderInline(text, keyPrefix) {
  // Models sometimes emit a literal "<br>" to force a line break inside a
  // single markdown table cell (plain newlines aren't valid there).
  const withBreaksMarked = text.split(/<br\s*\/?>/i)
  return withBreaksMarked.flatMap((segment, segIndex) => {
    const parts = segment.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={`${keyPrefix}-${segIndex}-${i}`}>{part.slice(2, -2)}</strong>
      }
      return <span key={`${keyPrefix}-${segIndex}-${i}`}>{part}</span>
    })
    if (segIndex < withBreaksMarked.length - 1) {
      parts.push(<br key={`${keyPrefix}-br-${segIndex}`} />)
    }
    return parts
  })
}

function isTableBlock(lines) {
  return lines.length >= 2 && lines.every((l) => l.trim().startsWith('|')) && /^\|[\s-:|]+\|$/.test(lines[1].trim())
}

function renderTable(lines, key) {
  const cells = (line) =>
    line
      .trim()
      .replace(/^\||\|$/g, '')
      .split('|')
      .map((c) => c.trim())

  const header = cells(lines[0])
  const rows = lines.slice(2).map(cells)

  return (
    <table className="md-table" key={key}>
      <thead>
        <tr>
          {header.map((h, i) => (
            <th key={i}>{renderInline(h, `th-${i}`)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, r) => (
          <tr key={r}>
            {row.map((cell, c) => (
              <td key={c}>{renderInline(cell, `td-${r}-${c}`)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function isListBlock(lines, pattern) {
  return lines.length >= 1 && lines.every((l) => pattern.test(l.trim()))
}

export default function renderMarkdown(text) {
  if (!text) return null
  const blocks = text.split(/\n{2,}/)

  return blocks.map((block, blockIndex) => {
    const lines = block.split('\n').filter((l) => l.trim() !== '')
    if (lines.length === 0) return null

    if (isTableBlock(lines)) {
      return renderTable(lines, `block-${blockIndex}`)
    }

    if (isListBlock(lines, /^[-*]\s+/)) {
      return (
        <ul key={`block-${blockIndex}`}>
          {lines.map((line, i) => (
            <li key={i}>{renderInline(line.replace(/^[-*]\s+/, ''), `li-${i}`)}</li>
          ))}
        </ul>
      )
    }

    if (isListBlock(lines, /^\d+\.\s+/)) {
      return (
        <ol key={`block-${blockIndex}`}>
          {lines.map((line, i) => (
            <li key={i}>{renderInline(line.replace(/^\d+\.\s+/, ''), `li-${i}`)}</li>
          ))}
        </ol>
      )
    }

    return (
      <p key={`block-${blockIndex}`}>
        {lines.map((line, i) => (
          <span key={i}>
            {renderInline(line, `line-${i}`)}
            {i < lines.length - 1 && <br />}
          </span>
        ))}
      </p>
    )
  })
}
