#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

import random
import logging
import operator
from collections import defaultdict
from messages import Upload, Request
from util import even_split
from peer import Peer

class AccStd(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.optimistic_peer = 0
    
    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        np_set = set(needed_pieces)  # sets support fast intersection ops.


        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)

        available_count = defaultdict(int)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))
            for piece in p.available_pieces:
                available_count[piece] += 1
        rarity_list = list(dict(sorted(available_count.items(), key=lambda item: item[1])).keys())

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        requests = []   # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)

        if len(history.downloads) == 0:
            chosen_peers = []
            for p in peers:
                if p.available_pieces != [] and len(chosen_peers) <= 2:
                    chosen_peers.append(p)
        else:
            agent_downloads = history.downloads[-1]
            aggregate_dict = defaultdict(int)
            for download in agent_downloads:
                aggregate_dict[download.from_id] += download.blocks
            sorted_peers_dict = dict( sorted(aggregate_dict.items(), key=operator.itemgetter(1),reverse=True))
            chosen_peers_ids = list(sorted_peers_dict.keys())[:3]
            chosen_peers = [peer for peer in peers if peer.id in chosen_peers_ids]

        if history.current_round() % 3 == 0:
            print(history.current_round(), "round")
            self.optimistic_peer = random.choice(peers)
            chosen_peers.append(self.optimistic_peer)
        else:
            chosen_peers.append(self.optimistic_peer)
        
        print(chosen_peers, "chosen peers!")

        for peer in chosen_peers:
            piece_id = False
            for piece in rarity_list:
                if piece in peer.available_pieces and piece in needed_pieces:
                    piece_id = piece
                    print(piece, "We need this!")
                    start_block = self.pieces[piece_id]
                    r = Request(self.id, peer.id, piece_id, start_block)
                    requests.append(r)

        # Sort peers by id.  This is probably not a useful sort, but other 
        # sorts might be useful
        #peers.sort(key=lambda p: p.id)
        # request all available pieces from all peers!
        # (up to self.max_requests from each)

        # for peer in peers:
        #     av_set = set(peer.available_pieces)
        #     isect = av_set.intersection(np_set)
        #     n = min(self.max_requests, len(isect))
        #     # More symmetry breaking -- ask for random pieces.
        #     # This would be the place to try fancier piece-requesting strategies
        #     # to avoid getting the same thing from multiple peers at a time.
        #     for piece_id in random.sample(isect, n):
        #         # aha! The peer has this piece! Request it.
        #         # which part of the piece do we need next?
        #         # (must get the next-needed blocks in order)
        #         start_block = self.pieces[piece_id]
        #         r = Request(self.id, peer.id, piece_id, start_block)
        #         requests.append(r)

        return requests

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")

            #request = random.choice(requests)
            chosen = [request.requester_id for request in requests]
            # Evenly "split" my upload bandwidth among the one chosen requester
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
