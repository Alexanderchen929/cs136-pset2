#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

import random
import logging

from collections import defaultdict
from messages import Upload, Request
from util import even_split
from peer import Peer

class RarityTracker(object):
    def __init__(self,current_block):
        self.current_block = current_block
        self.peers_with = []
        self.num_peers = 0
        
    def add_peer(self,peer):
        self.peers_with.append(peer)
        self.num_peers += 1

class AccTyrant(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"

        #1 of bittyrant pseudocode
        self.d = {}
        self.u = {}
        self.gamma = 0.1
        self.alpha = 0.2
        self.cp_set = set()

    def update_du(self, history):
        #Step 5, for each unchoked peer
        if self.cp_set != set():
            last_downloads_ids = [download.from_id for download in history.downloads[-1]]
            last_downloads_blocks = [download.blocks for download in history.downloads[-1]]
            for peer in self.cp_set:
                if peer not in last_downloads_ids:
                    self.u[peer] = (1+self.alpha)*self.u[peer]
                else:
                    self.d[peer] = last_downloads_blocks[last_downloads_ids.index(peer)]
                    if len(self.cp_set) >=3:
                        second_downloads = [download.from_id for download in history.downloads[-2]]
                        third_downloads = [download.from_id for download in history.downloads[-3]]
                        if peer in second_downloads and peer in third_downloads:
                            self.u[peer] = (1-self.gamma)*self.u[peer]


    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        random.shuffle(needed_pieces)
        np_set = set(needed_pieces)  # sets support fast intersection ops.
        
        #A: a list of RarityTracker objects for every piece we need
        rarity_list = {piece: RarityTracker(self.pieces[piece]) for piece in needed_pieces}
        


        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))
        logging.debug("%s still here. Here are some peers:" % self.id)
        
        

        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))
            # find the pieces they have that we want
            av_set = set(p.available_pieces)
            wanted_pieces = av_set.intersection(np_set)
            for piece in wanted_pieces:
                rarity_list[piece].add_peer(p.id)
        
        logging.debug(rarity_list)
        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))
        
        rarity_list = dict(sorted(rarity_list.items(),key=lambda x: x[1].num_peers))
        requests = []   # We'll put all the things we want here
        for piece in rarity_list.keys():
            peers = rarity_list[piece].peers_with
            random.shuffle(peers)
            start_block = self.pieces[piece]
            for peer in peers:
                r = Request(self.id,peer,piece,start_block)
                requests.append(r)
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
        #2 initialize d_ij and u_ij based on initial estimates. We should make heuristic guess here
        if round == 0:
            for peer in peers:
                self.d[peer.id] = 1
                self.u[peer.id] = 1
        downloads = history.downloads
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
        if round == 0:
            print('You shouldnt be getting requests in round 0, something is broken')
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # get the most recent download history
            recent_downloads = downloads[-1]
            
            # create a running tally of how many blocks each peer let us download
            # MAYBE shuffle downloads to introduce more randomness?
            download_totals = defaultdict(int)
            for download in recent_downloads:
                download_totals[download.from_id] += download.blocks
                
            # sort by ratio and select enough until it hits capacity
            ratios = {i: self.d[i] / self.u[i] for i in self.d.keys()}
            peer_ranking = dict(sorted(ratios.items(),key=lambda x: x[1], reverse=True))
            cumulative_capacity = 0
            for peer_info in peer_ranking.items():
                if cumulative_capacity <= self.up_bw:
                    cumulative_capacity += peer_info[1]
                    self.cp_set.add(peer_info[0])
                else:
                    break
            
            # # now remove the chosen from the list of all peers, and select the 
            # # optimistic unchoke
            # all_peers = [p.id for p in peers]
            # ap_set = set(all_peers)
            # optimistic_pool = list(ap_set.difference(cp_set))
            # optimistic_unchoke = random.choice(optimistic_pool)
            
            # # add the optimistic unchoke to chosen_peers
            # chosen_peers.append(optimistic_unchoke)
            # cp_set = set(chosen_peers)
            
            # get a list of all peers requesting to download from us.
            request_ids = [request.requester_id for request in requests]
            rp_set = set(request_ids)
            
            # now take the intersection of peers requesting, and the chosen peers
            # to find who we are uploading to
            chosen = list(rp_set.union(self.cp_set))

            #bandwidths are proportional
            bws = even_split(self.up_bw,len(chosen))
            

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]

        
            
        return uploads