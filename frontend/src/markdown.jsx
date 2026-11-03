// Minimal, dependency-free renderer for the small subset of markdown the
// backend's prompts actually produce: headings, **bold**, *italic*,
// "- "/"1. " lists (including mixed in with plain sentences), "---"
// rules, and "|"-delimited tables. Not a general markdown parser - just
// enough to stop raw "#"/"**"/"*"/"|"/"---" characters from showing up
// as literal text in the chat transcript.

function renderInline(text, keyPrefix) {
  // Models sometimes emit a literal "<br>" to force a line break inside a
  // single markdown table cell (plain newlines aren't valid there).
  const withBreaksMarked = text.split(/<br\s*\/?>/i)
  return withBreaksMarked.flatMap((segment, segIndex) => {
    // Bold is tried before italic at every position so "**x**" is never
    // misread as an italic span starting with a stray "*".
    const parts = segment.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={`${keyPrefix}-${segIndex}-${i}`}>{part.slice(2, -2)}</strong>
      }
      if (part.startsWith('*') && part.endsWith('*')) {
        return <em key={`${keyPrefix}-${segIndex}-${i}`}>{part.slice(1, -1)}</em>
      }
      return <span key={`${keyPrefix}-${segIndex}-${i}`}>{part}</span>
    })
    if (segIndex < withBreaksMarked.length - 1) {
      parts.push(<br key={`${keyPrefix}-br-${segIndex}`} />)
    }
    return parts
  })
}

const HEADING_PATTERN = /^(#{1,6})\s+(.*)$/
const RULE_PATTERN = /^(-{3,}|\*{3,}|_{3,})$/
const BULLET_PATTERN = /^[-*]\s+/
const NUMBERED_PATTERN = /^\d+\.\s+/

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

// Groups the lines of one block by type (bullet list / numbered list /
// plain text) in order, so a block that mixes an intro sentence, a list,
// and a closing sentence - with no blank lines between them, which models
// do constantly - still renders each part correctly instead of falling
// back to one literal paragraph.
function groupLines(lines) {
  const groups = []
  for (const rawLine of lines) {
    const line = rawLine.trim()
    let type = 'p'
    let content = line
    if (BULLET_PATTERN.test(line)) {
      type = 'ul'
      content = line.replace(BULLET_PATTERN, '')
    } else if (NUMBERED_PATTERN.test(line)) {
      type = 'ol'
      content = line.replace(NUMBERED_PATTERN, '')
    }
    const last = groups[groups.length - 1]
    if (last && last.type === type) {
      last.items.push(content)
    } else {
      groups.push({ type, items: [content] })
    }
  }
  return groups
}

function renderGroups(lines, keyPrefix) {
  return groupLines(lines).map((group, gi) => {
    const key = `${keyPrefix}-g${gi}`
    if (group.type === 'ul') {
      return (
        <ul key={key}>
          {group.items.map((item, i) => (
            <li key={i}>{renderInline(item, `${key}-li${i}`)}</li>
          ))}
        </ul>
      )
    }
    if (group.type === 'ol') {
      return (
        <ol key={key}>
          {group.items.map((item, i) => (
            <li key={i}>{renderInline(item, `${key}-li${i}`)}</li>
          ))}
        </ol>
      )
    }
    return (
      <p key={key}>
        {group.items.map((line, i) => (
          <span key={i}>
            {renderInline(line, `${key}-line${i}`)}
            {i < group.items.length - 1 && <br />}
          </span>
        ))}
      </p>
    )
  })
}

/**
 * @param {string} text
 * @param {{ suppressTables?: boolean }} [options] - suppressTables omits
 *   rendered tables entirely; used when a structured tool card below the
 *   message already shows the same data, so it isn't shown twice.
 */
export default function renderMarkdown(text, options = {}) {
  if (!text) return null
  const { suppressTables = false } = options
  const blocks = text.split(/\n{2,}/)

  return blocks
    .map((block, blockIndex) => {
      let lines = block.split('\n').filter((l) => l.trim() !== '')
      if (lines.length === 0) return null

      if (lines.length === 1 && RULE_PATTERN.test(lines[0].trim())) {
        return <hr key={`block-${blockIndex}`} className="md-rule" />
      }

      const headingMatch = lines[0].trim().match(HEADING_PATTERN)
      let heading = null
      if (headingMatch) {
        const level = Math.min(headingMatch[1].length, 4)
        const Tag = `h${level + 2}` // model h1-h6 -> rendered h3-h6, so it never outsizes the chat bubble
        heading = <Tag key={`heading-${blockIndex}`} className="md-heading">{renderInline(headingMatch[2], `h-${blockIndex}`)}</Tag>
        lines = lines.slice(1)
        if (lines.length === 0) return heading
      }

      if (isTableBlock(lines)) {
        if (suppressTables) return heading
        return (
          <div key={`block-${blockIndex}`}>
            {heading}
            {renderTable(lines, `table-${blockIndex}`)}
          </div>
        )
      }

      return (
        <div key={`block-${blockIndex}`}>
          {heading}
          {renderGroups(lines, `block-${blockIndex}`)}
        </div>
      )
    })
    .filter(Boolean)
}
