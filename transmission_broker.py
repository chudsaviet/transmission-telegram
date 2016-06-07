from transmissionrpc import Client
from transmissionrpc import TransmissionError


class NotAuthorizedChatException(Exception):
    pass


class TransmissionBroker:
    def __init__(self, config, persistence):
        self.conn = Client(
            config.address,
            port=config.port,
            user=config.user,
            password=config.password
        )
        self.secret = config.secret
        self.persistence = persistence

    @staticmethod
    def pretty_torrents_list(torrents):
        info_list = list()
        for torrent in torrents:
            info_list.append(
                '%s: %s, %s : %d%%' %
                (torrent.id, torrent.name, torrent.status, torrent.percentDone * 100)
            )
        return '\n'.join(info_list)

    def retrieve_list(self, chat_id):
        torrents = self.conn.get_torrents()

        return TransmissionBroker.pretty_torrents_list(torrents)

    def add_torrent(self, chat_id, url):
        self.conn.add_torrent(url)

    def remove_torrent(self, chat_id, torrent_ids):
        # Check is not embedded to transmissionrpc module, so we have to do it ourselves
        missing_torrents = list()
        torrents = self.conn.get_torrents()
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

        self.conn.remove_torrent(torrent_ids)

    def check_chat_authorization(self, chat_id):
        if not self.persistence.check_chat_id(chat_id):
            raise NotAuthorizedChatException()

    def authorize_chat(self, chat_id, secret):
        if self.secret == secret:
            self.persistence.add_chat_id(chat_id)
            return True
        else:
            return False
