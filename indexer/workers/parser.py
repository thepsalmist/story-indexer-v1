"""
metadata parser pipeline worker
"""

import logging

import chardet

# PyPI:
import mcmetadata
from pika.adapters.blocking_connection import BlockingChannel

# local:
from indexer.story import BaseStory
from indexer.worker import StoryWorker, run

logger = logging.getLogger(__name__)


class Parser(StoryWorker):
    def process_story(
        self,
        chan: BlockingChannel,
        story: BaseStory,
    ) -> None:
        rss = story.rss_entry()
        raw = story.raw_html()

        link = rss.link
        # XXX quarantine Story if no link or HTML???
        if link:
            try:
                html = raw.unicode

                # metadata dict
                # may raise mcmetadata.exceptions.BadContentError
                try:
                    mdd = mcmetadata.extract(link, html)
                    logger.info(f"MDD keys {mdd.keys()}")

                    with story.content_metadata() as cmd:
                        # XXX assumes identical item names!!
                        #       could copy items individually with type checking
                        #       if mcmetadata returned TypedDict?
                        for key, val in mdd.items():
                            if hasattr(cmd, key):  # avoid hardwired exceptions list?!
                                setattr(cmd, key, val)
                    extraction_label = mdd.get("text_extraction_method", "")

                    self.send_story(chan, story)
                    self.incr("parsed-stories", labels=[("method", extraction_label)])
                except Exception as e:
                    logger.error(e)
            except Exception as e:
                logger.info(e)


if __name__ == "__main__":
    run(Parser, "parser", "metadata parser worker")
