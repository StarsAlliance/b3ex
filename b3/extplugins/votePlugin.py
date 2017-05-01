#
# votePlugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2013 Simon "madPO" Zor'kin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# Changelog:
#
#
__author__ = 'madPO'
__version__ = '27.08.13'

import b3
import b3.events
import b3.plugin
import re
import time


class VotepluginPlugin(b3.plugin.Plugin):
    requiresConfigFile = True

    _commands = {}
    _adminPlugin = None
    _voteState = 'off'
    _voteTarget = ''
    _playerToVote = None
    _voteIniter = ''
    _votedList = []
    _numYes = 0
    _numNo = 0
    _voteTime = 45
    _countdown = 0
    _minVotes = 0
    _minVoteRatio = 2
    _mapList = []
    _voteTimeAlowed = 45
    _voteAlowed = False
    _voteK = 0

    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
        return None

    def onLoadConfig(self):
        # load our settings
        self.verbose('Loading config <Started> ...')
        self._voteTime = self.config.getint('settings','voteTime')
        self._minVoteRatio = self.config.getint('settings','minVoteRatio')
        self._voteTimeAlowed = self.config.getint('settings','votetimestart')
        for e in self.config.get('maps/map'):
            self._mapList.append(e.text)
        self.verbose('Loading config <Stoped>.')

    def onStartup(self):
         """\
         Initialize plugin settings
         """

         # get the admin plugin so we can register commands
         self.registerEvent(b3.events.EVT_GAME_MAP_CHANGE)
         self._adminPlugin = self.console.getPlugin('admin')
         self.verbose('Loading admin plugin')
         if not self._adminPlugin:
             # something is wrong, can't start without admin plugin
             self.error('Could not find admin plugin')
             return False
         self.verbose('Loading commans...')
         #register our commands\
         if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp

                func = self.getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)

         self.verbose('votePlugin start!!!')

    def onEvent(self, event):
        if event.type == b3.events.EVT_GAME_MAP_CHANGE:
            self.resetVotes()
            self._voteAlowed = True
            self.verbose('Start vote')
            time.sleep(5)
            self.console.cron + b3.cron.OneTimeCronTab(self.startVote,  '*/%d'%(self._voteTimeAlowed))


    
    #cmd !maplist
    def cmd_maplist(self,  data,  client,  cmd=None):
        cmd.sayLoudOrPM(client,"Maps available for voting: " + ", ".join(self._mapList))

    def resetVotes(self):
        self._voteState = "off"
        self._voteTarget = ""
        self._playerToVote = None
        self._voteIniter = ""
        self._voteReason = ""
        self._votedList = []
        self._numYes = 0
        self._numNo = 0
        self._countdown = -1
        self.console.write("b3_message ^7")
	
    def startVote(self):
        if self._voteAlowed != False:
            self.console.say('^2Voting is open in the next %d seconds'%(self._voteTimeAlowed*2))
            time.sleep(5)
            self.console.say('^2Use !votemap mp_name')
            self.console.cron + b3.cron.OneTimeCronTab(self.stopVote,  '*/%d'%(self._voteTimeAlowed))

    def stopVote(self):
        if self._voteAlowed != False:
                self.console.say('^2Voting is closed')
                self._voteAlowed = False
                self.verbose('Stop vote')
                self.console.cron + b3.cron.OneTimeCronTab(self.stopVote,  "")

    def resolveVote(self):
        if self._numYes >= self._minVotes:
            self.console.say('^2Vote passed')
            time.sleep(1)
            if self._voteState == "Map":
                self.console.say('^2Changing map to %s'%self._voteTarget)
                time.sleep(3)
                self.console.write("b3_message ^7")
                self.console.write('map %s'%self._voteTarget)
                self.resetVotes()
        else:
            self.console.say('^2Vote failed. Yes:(^2%d^2) No:(^1%d^2)'%(self._numYes,self._numNo))
            self.resetVotes()

    def minVotes(self):
        return len(self.console.clients.getList())/self._minVoteRatio + 1

    #cmd !yes
    def cmd_voteyes(self, data, client=None, cmd=None):
         if self._voteState == "off":
            cmd.sayLoudOrPM(client, '^7Voting impossible')
         else:
            if client not in self._votedList:
                self._numYes += 1
                self._votedList.append(client)
                client.message('^7 You have voted ^2yes')
            else:
                client.message('^7 You have already voted')

    #cmd !no
    def cmd_voteno(self, data, client=None, cmd=None):
         if self._voteState == "off":
            cmd.sayLoudOrPM(client, '^7Voting impossible')
         else:
            if client not in self._votedList:
                self._numNo += 1
                self._votedList.append(client)
                client.message('^7 You have voted ^1no')
            else:
                client.message('^7 You have already voted')

    def updateCountdown(self):
        self.console.write('b3_message ^7%s vote for %s ending in %d (%d/%d)'%(self._voteState, self._voteTarget,self._countdown,self._numYes,self._minVotes))
        self._countdown -= 1
        if self._countdown >= 0 and self._numYes < self._minVotes:
            self.console.cron + b3.cron.OneTimeCronTab(self.updateCountdown,  "*/1")
        else:
            self.resolveVote()

    #cmd !veto
    def cmd_veto(self, data, client=None, cmd=None):
        """
        <veto> - Veto the current vote
        """
        if self._voteState == "off":
            cmd.sayLoudOrPM(client, '^7Voting impossible')
        else:
            self.console.say('^2Administrator vetoes vote')
            self.resetVotes()

    #cmd !votestatus
    def cmd_votestatus(self, data, client=None, cmd=None):
        if self._voteState == "off":
            cmd.sayLoudOrPM(client, '^7No vote in session')
        else:
            cmd.sayLoudOrPM(client, '^7Current votes ^2yes^7:%d of %d,^1no^7:%d'%(self._numYes, self._minVotes, self._numNo))

    #cmd !votemap
    def cmd_votemap(self, data, client=None, cmd=None):
        """\
        <map> - Map to vote on
        """
        if self._voteAlowed == False:
            client.message('^7Voting impossible')
        else:
            if self._voteState != "off":
                client.message('^2Vote is already in session')
                return True

            m = self._adminPlugin.parseUserCmd(data)

            if not m:
                client.message('^7Invalid parameters, you must supply a map')
                return False

            elif m[0] not in self._mapList:
                client.message('^7%s is an invalid map'%m[0])
                time.sleep(1)
                client.message('^7Use !maplist')
                return False
            else:
                self._voteTarget = m[0]
                self._voteState = "Map"
                self._countdown = self._voteTime
                self._minVotes = self.minVotes()
                self.console.say('^2Map voting for %s has commenced'%self._voteTarget)
                time.sleep(0.2)
                self.console.say('^2%s votes needed to pass'%self._minVotes)
                time.sleep(0.2)
                self.console.say('^2Type !yes or !no to vote')
                self.updateCountdown()
                return True
    #cmd !maprestart
    def cmd_maprestart(self, data, client, cmd=None):
        """\
        Restart the current map.
        """
        self.console.say('^2Fast restart will be executed')
        time.sleep(5)
        self.console.write('fast_restart')
        return True
