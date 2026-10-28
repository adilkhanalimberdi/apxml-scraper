from urllib.parse import urljoin, urlparse


def normalize(url: str) -> str:
    """Strip fragment, query and trailing slash (the site 308-redirects slash URLs)."""
    parts = urlparse(url)
    return parts._replace(query="", fragment="", path=parts.path.rstrip("/")).geturl()


def to_absolute(base_url: str, href: str) -> str:
    return normalize(urljoin(base_url + "/", href))


def course_slug(course_url: str) -> str:
    """https://apxml.com/courses/<slug>[/...] -> <slug>"""
    segments = [s for s in urlparse(course_url).path.split("/") if s]
    if len(segments) < 2 or segments[0] != "courses":
        raise ValueError(f"Not a course URL: {course_url}")
    return segments[1]
