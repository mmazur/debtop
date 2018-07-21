# pylint: disable=missing-docstring
import shutil
import gzip
import os.path

import urllib.request
from urllib.error import URLError, HTTPError # pylint: disable=unused-import


class DEBIndex:
    """Fetch, parse and summarize a remote deb index file"""
    # pylint: disable=too-few-public-methods
    def __init__(self, arch, baseurl='http://ftp.uk.debian.org/debian/dists/stable/main/'):
        self._arch = arch
        basename = 'Contents-{}.gz'.format(arch)
        self._fullurl = baseurl + basename
        self._localpath = '.cache/' + basename
        self._debcounter = {}
        self._scoreboard = {}
        self._nonconforming_lines = 0

        self._fetch_index()
        self._parse_index()
        self._compute_scoreboard()


    def _fetch_index(self):
        """Fetch a remote index file and store it locally (if it's not already present)

        Common exceptions: URLError, HTTPError if there's an issue with fetching the index"""
        # TODO: compare file size and timestamp
        if not os.path.isfile(self._localpath):
            # Don't try to intercept any exceptions; let the code using this class deal
            # with them if it so wishes
            with urllib.request.urlopen(self._fullurl) as response:
                with open(self._localpath, 'wb') as local_file:
                    shutil.copyfileobj(response, local_file)


    def _parse_index(self):
        """Parse local index file, compute file counts for each deb"""
        with gzip.open(self._localpath, 'rt') as index_file:
            borkedlines = 0
            debcounter = {}

            for lineno, line in enumerate(index_file, start=1):
                columns = line.strip().rsplit(maxsplit=1)

                # Quietly ignore malformed lines (per spec)
                if len(columns) != 2:
                    borkedlines += 1
                    continue

                path, locations = columns[0], columns[1]

                # Ignore optional header (per spec)
                if lineno == 1 and path == 'FILE' and locations == 'LOCATION':
                    continue

                # Packages may be qualified with area/section names
                qdebs = [longname.split('/') for longname in locations.split(',')]
                max_qualifier_depth = max([len(qdeb) for qdeb in qdebs])

                # Ignore line with too many slashes in a qualified name (per spec)
                if max_qualifier_depth > 3:
                    borkedlines += 1
                    continue

                # Now we're sure everything's fine
                for qdeb in qdebs:
                    deb = qdeb[-1]
                    debcounter[deb] = debcounter.get(deb, 0) + 1

                self._nonconforming_lines = borkedlines
                self._debcounter = debcounter


    def _compute_scoreboard(self):
        """Compute a dict of file counts, with a list of debs linked to each"""
        scoreboard = {}

        for deb, counter in self._debcounter.items():
            if counter not in scoreboard:
                scoreboard[counter] = []
            scoreboard[counter].append(deb)

        self._scoreboard = scoreboard


    def get_top_packages(self, max_place=10):
        """Return a sorted list of (place, deb, fileno) tupples where place <= max_place

        Note: returned list might be longer than max_place entries when ties are present"""
        scoreboard = self._scoreboard
        final_standings = []

        for score in sorted(scoreboard.keys(), reverse=True)[:max_place]:
            place = len(final_standings)+1
            if place > max_place:
                break
            debs = sorted(scoreboard[score])
            for deb in debs:
                final_standings.append((place, deb, score))

        return final_standings
