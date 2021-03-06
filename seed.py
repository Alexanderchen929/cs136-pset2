#!/usr/bin/python

import random
from messages import Upload, Request
from util import even_split
from peer import Peer

class Seed(Peer):
    def requests(self, peers, history):
        # Seeds don't need anything.
        return []

    def update_du(self, history):
        pass

    def uploads(self, requests, peers, history):
        max_upload = 4  # max num of peers to upload to at a time
        requester_ids = list(set([r.requester_id for r in requests]))

        n = min(max_upload, len(requester_ids))
        if n == 0:
            return []
        bws = even_split(self.up_bw, n)
        uploads = [Upload(self.id, p_id, bw)
                   for (p_id, bw) in zip(random.sample(requester_ids, n), bws)]
        
        return uploads
