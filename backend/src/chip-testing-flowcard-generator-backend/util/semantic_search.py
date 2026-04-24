import re

from schema.knowledge import SemanticSearchHit


def _split_sections(raw_result: str) -> tuple[str, str, str]:
    sections: list[list[str]] = [[]]

    for line in raw_result.replace('\r\n', '\n').split('\n'):
        if line.strip() == '---' and len(sections) < 3:
            sections.append([])
            continue
        sections[-1].append(line)

    while len(sections) < 3:
        sections.append([])

    title_part, hierarchy_part, content_part = ('\n'.join(section).strip() for section in sections[:3])
    if not content_part and len(sections) > 3:
        extra_sections = ['\n'.join(section).strip() for section in sections[3:]]
        content_part = '\n'.join([part for part in extra_sections if part]).strip()

    return title_part, hierarchy_part, content_part


def parse_semantic_search_hit(raw_result: str) -> SemanticSearchHit:
    title_part, hierarchy_part, content_part = _split_sections(raw_result)
    document_title = re.sub(r'^文档标题[:：]\s*', '', title_part).strip()
    hierarchy: list[str] = []

    for line in hierarchy_part.splitlines():
        line = line.strip()
        if line.startswith('#'):
            hierarchy.append(re.sub(r'^#+\s*', '', line).strip())

    return SemanticSearchHit(
        document_title=document_title,
        hierarchy=[item for item in hierarchy if item],
        content=content_part.strip()
    )
