from collections import namedtuple
ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'

headers = {
    "User-Agent": ua, "Accept-Language": "en-US, en;q=0.5", 'Content-Type': 'application/json; charset=utf-8'}


class Filter:
    def __init__(self, data: dict, duration: int, result_count=6):
        self.duration = duration
        self.result_count = result_count
        self.data = data

    @property
    async def video_id(self):
        return await self.get_params()

    @staticmethod
    def convert_to_seconds(duration: list):
        dur_seconds = 0
        if len (duration) == 1:
            dur_seconds = int (duration[0])
        elif len (duration) == 2:
            min = int (duration[0]) * 60
            dur_seconds = min + int (duration[1])
        elif len (duration) == 3:
            min = int (duration[1]) * 60
            hr = int (duration[0]) * 3600
            dur_seconds = int (duration[0]) + min + hr
        return int (dur_seconds)

    async def get_params(self):
        params_list = []
        VideoData = namedtuple ('VideoData', 'id length views owner')
        base_js = self.data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0][
            'itemSectionRenderer']['contents']
        result_list = [base_js[i] for i in range (1, self.result_count + 1) if 'videoRenderer' in base_js[i].keys ()]
        for data in result_list:
            video_id = data['videoRenderer']['videoId']
            length = data['videoRenderer']['lengthText']['simpleText'].split(':')
            views = data['videoRenderer']['viewCountText']['simpleText'].rstrip(' views').split(',')
            try:
                owner_status = data['videoRenderer']['ownerBadges'][0]['metadataBadgeRenderer']['accessibilityData'][
                    'label']
            except KeyError:
                owner_status = None

            params_list.append (VideoData (video_id, self.convert_to_seconds (length), int (''.join (views)), owner_status))
        if not params_list:
            return None
        best_data = params_list[0]
        for i, data in enumerate (params_list):
            if (best_data.views < data.views) and (self.duration - 40 < best_data.length < self.duration + 40):
                best_data = params_list[i]

        del params_list[params_list.index(best_data)]
        second_data = params_list[0]
        for i, data in enumerate (params_list):
            if (second_data.views < data.views) and (self.duration - 40 < best_data.length < self.duration + 40):
                second_data = params_list[i]

        return best_data.id, second_data.id




