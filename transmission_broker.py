from transmissionrpc import Client
from transmissionrpc import TransmissionError


class NoConnectionException(Exception):
    pass


class TransmissionBroker:
    def __init__(self):
        self.conn = dict()

    @staticmethod
    def pretty_torrents_list(torrents):
        info_list = list()
        for torrent in torrents:
            info_list.append(
                '%s: %s, %s : %d%%' %
                (torrent.id, torrent.name, torrent.status, torrent.percentDone * 100)
            )
        return '\n'.join(info_list)

    def open_connection(self, chat_id, credentials):
        tc = Client(
            credentials.address,
            port=credentials.port,
            user=credentials.user,
            password=credentials.password
        )
        if tc:
            self.conn[chat_id] = tc

    def retrieve_list(self, chat_id):

        torrents = self.conn[chat_id].get_torrents()

        return TransmissionBroker.pretty_torrents_list(torrents)

    def add_torrent(self, chat_id, url):
        self.conn[chat_id].add_torrent(url)

    def remove_torrent(self, chat_id, torrent_ids):

        # Check is not embedded to transmissionrpc module, so we have to do it ourselves
        missing_torrents = list()
        torrents = self.conn[chat_id].get_torrents()
        for tid in torrent_ids:
            id_found = False
            for torrent in torrents:
                if tid == torrent.id:
                    id_found = True
                    break
            if not id_found:
                missing_torrents.append(tid)

        if len(missing_torrents) > 0:
            raise TransmissionError('Torrents %s not found' % missing_torrents)

        self.conn[chat_id].remove_torrent(torrent_ids)

    def check_connection(self, chat_id):
        if chat_id not in self.conn:
            raise NoConnectionException()
