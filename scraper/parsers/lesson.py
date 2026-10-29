import json
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

from scraper.models import Chart, Image, Lesson
from scraper.parsers.base import BaseParser
from utils.url import normalize

KEEP_ATTRS = {"href", "src", "alt", "title", "colspan", "rowspan", "data-chart"}
DROP_TAGS = ("script", "style", "svg", "noscript", "iframe")
UI_BUTTONS = {"report issue", "mark as complete", "write a review"}


class LessonPageParser(BaseParser[Lesson]):
    """Parses a lesson page into a Lesson (content, images, charts).

    Works on a Lesson stub from CoursePageParser: pass it via `parse_into`.
    """

    def parse(self, html: str, url: str) -> Lesson:
        lesson = Lesson(slug=url.rstrip("/").rsplit("/", 1)[-1], title="", url=url, order=0)
        return self.parse_into(lesson, html)

    def parse_into(self, lesson: Lesson, html: str) -> Lesson:
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.find("h1")
        if h1 is None:
            return lesson
        lesson.title = lesson.title or h1.get_text(strip=True)

        content = soup.select_one(".course-content")
        if content is None:  # quiz / project pages: no article body, only a spec block
            content = h1.parent
            h1.extract()
        parsed = urlparse(lesson.url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        lesson.charts = self._extract_charts(content)
        self._replace_math(content)
        self._handle_buttons(content)
        for tag in content.find_all(DROP_TAGS):
            tag.decompose()
        lesson.images = self._extract_images(content, base_url)
        self._strip_attributes(content)

        lesson.content_html = content.decode_contents().strip()
        lesson.content_markdown = markdownify(
            lesson.content_html, heading_style="ATX",
            escape_underscores=False, escape_asterisks=False, escape_misc=False,
        ).strip()
        return lesson

    @staticmethod
    def _extract_charts(content: Tag) -> list[Chart]:
        """Plotly charts and Graphviz diagrams carry their source in data attributes."""
        charts = []
        for node in content.select(".plotly-container, .graphviz-container"):
            if "plotly-container" in node.get("class", []):
                kind, id_attr, def_attr = "plotly", "data-plot-id", "data-plot-definition"
            else:
                kind, id_attr, def_attr = "graphviz", "data-graph-id", "data-graph-definition"
            chart_id = node.get(id_attr, f"{kind}-{len(charts) + 1}")
            definition = node.get(def_attr, "")
            if kind == "plotly":
                try:
                    definition = json.dumps(json.loads(definition), ensure_ascii=False)
                except ValueError:
                    pass
            charts.append(Chart(chart_id=chart_id, kind=kind, definition=definition))
            marker = Tag(name="div")
            marker["data-chart"] = chart_id
            marker.string = f"[{kind}: {chart_id}]"
            node.replace_with(marker)
        return charts

    @staticmethod
    def _replace_math(content: Tag) -> None:
        """Swap rendered KaTeX markup for its TeX source ($...$ / $$...$$)."""
        for node in content.select(".katex-display"):
            annotation = node.find("annotation")
            node.replace_with(f"\n$$\n{annotation.get_text()}\n$$\n" if annotation else "")
        for node in content.select(".katex"):
            annotation = node.find("annotation")
            node.replace_with(f"${annotation.get_text()}$" if annotation else node.get_text())

    @staticmethod
    def _handle_buttons(content: Tag) -> None:
        """Drop site UI buttons; keep labels of accordion/tab buttons (e.g. "References") as bold text."""
        for button in content.find_all("button"):
            label = button.get_text(" ", strip=True)
            if not label or label.lower() in UI_BUTTONS:
                button.decompose()
            else:
                strong = Tag(name="strong")
                strong.string = label
                button.replace_with(strong)

    @staticmethod
    def _extract_images(content: Tag, base_url: str) -> list[Image]:
        images = []
        for img in content.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src or src.startswith("data:"):
                img.decompose()
                continue
            signed = urljoin(base_url + "/", src)
            src = normalize(signed)  # drop the expiring S3 signature from what we store
            img["src"] = src
            images.append(Image(src=src, alt=img.get("alt", ""), fetch_url=signed))
        return images

    @staticmethod
    def _strip_attributes(content: Tag) -> None:
        for tag in content.find_all(True):
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in KEEP_ATTRS}
