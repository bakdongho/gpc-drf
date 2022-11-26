import json
import re

from bs4 import BeautifulSoup


class NotFoundSliceWord(Exception):
    pass


class NotFoundContentWord(Exception):
    pass


class HtmlParser:
    CONTENT_WORD = "ROOT_QUERY"
    START_SLICE_WORD = "window.__APOLLO_STATE__"
    END_SLICE_WORD = "window.__PLACE_STATE__"

    def parse(self, content: str) -> BeautifulSoup | None:
        if not content:
            return None
        soup = BeautifulSoup(content, "html.parser")
        return json.loads(self.extract_content(self.find_content(soup)))

    def extract_content(self, content: str) -> str | None:
        if not all((word in content for word in (self.START_SLICE_WORD, self.END_SLICE_WORD))):
            raise NotFoundSliceWord
        # 내가 원하는 부분을 찾아서 슬라이싱 후 json.loads를 통해 dict를 얻을 수 있다.
        start_idx = re.search(self.START_SLICE_WORD, content).end()
        end_idx = re.search(self.END_SLICE_WORD, content).start()
        return content[start_idx + 2 : end_idx].strip()[:-1]  # 2까지 자르는 이유는 = 제거, -1까지 자르는 이유는 ';' 제거

    def find_content(self, soup: BeautifulSoup) -> str | None:
        for script in soup.find("body").find_all("script"):
            if self.CONTENT_WORD in str(script):
                return str(script)
        raise NotFoundContentWord
