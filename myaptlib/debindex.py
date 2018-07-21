import urllib.request
import shutil
import gzip
import os.path


class DEBIndex:
    def __init__(self, arch, baseurl='http://ftp.uk.debian.org/debian/dists/stable/main/'):
        self._arch = arch
        # baseurl and basename are used per convention, but it's confusing
        # if you think about it :)
        self._baseurl = baseurl
        self._basename = 'Contents-{}.gz'.format(arch)
        self._fullurl = baseurl + self._basename
        self._localpath = '.cache/' + self._basename
        self._debcounter = {}
        self._scoreboard = {}
        self._nonconforming_lines = 0

        self._fetch_index()
        self._parse_index()
        self._compute_scoreboard()


    def _fetch_index(self):
        # TODO: compare file size and timestamp
        if not os.path.isfile(self._localpath):
            with urllib.request.urlopen(self._fullurl) as response:
                with open(self._localpath, 'wb') as f:
                    shutil.copyfileobj(response, f)


    def _parse_index(self):
        with gzip.open(self._localpath, 'rt') as f:
            borkedlines = 0
            debcounter = {}

            for lineno, line in enumerate(f, start=1):
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
        scoreboard = {}

        for deb, counter in self._debcounter.items():
            if counter not in scoreboard:
                scoreboard[counter] = []
            scoreboard[counter].append(deb)

        self._scoreboard = scoreboard


    def get_top_packages(self, topN=10):
        scoreboard = self._scoreboard
        final_standings = []

        for score in sorted(scoreboard.keys(), reverse=True)[:topN]:
            place = len(final_standings)+1
            if place > topN:
                break
            debs = sorted(scoreboard[score])
            for deb in debs:
                final_standings.append((place, deb, score))

        return final_standings

