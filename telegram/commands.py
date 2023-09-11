import logging
import telebot, telebot.types

import zabbix_frontend

class CommandHandler:
    def __init__(self, telegram_token, zapi, telegram_users):
        self.zapi = zapi
        self.telegram_users = telegram_users

        try:
            telebot.apihelper.ENABLE_MIDDLEWARE = True
            self.bot = telebot.TeleBot(telegram_token, parse_mode='HTML')
        except:
            print(sys.exc_info()[1])
            sys.exit(1)

        logging.info('Bot info from Telegram: %s', self.bot.get_me())


        #######################################################################
        # Message middleware handlers
        #######################################################################

        ### Logging
        @self.bot.middleware_handler()
        def debug_all_messages(bot_instance, message):
            logging.debug('********** Received message: %s', message)


        ### Reject unknown senders
        @self.bot.message_handler(func=lambda msg: str(msg.from_user.id) not in self.telegram_users)
        def reject_unknown_senders(message):
            self.bot.reply_to(message, "I don't know you. Go away")


        ### Message text normalization
        @self.bot.middleware_handler(update_types = ['message'])
        def remove_leading_slash(bot_instance, message):
            if not message.text.startswith('/'):
                logging.debug('Adding leading / to message [%s]', message.text)
                message.text = '/' + message.text



        #######################################################################
        # Message handlers
        #######################################################################
        @self.bot.message_handler(commands=['start'])
        def cmd_start(message):
            zabbix_user = self.telegram_users[str(message.from_user.id)]
            self.bot.reply_to(message,
                     "Howdy <b>%s %s</b> (Zabbix username <b>%s</b>), how are you doing?" % (zabbix_user['first_name'], zabbix_user['surname'], zabbix_user['zabbix_username']))


        @self.bot.message_handler(commands=['help'])
        def cmd_help(message):
            self.bot.reply_to(message, "Allowed commands: " + str(dir(self.__init__)))


        @self.bot.message_handler(commands=['access'])
        def cmd_access(message):
            zabbix_user = self.telegram_users[str(message.from_user.id)]

            ## Result in an array of these:
            ## {
            ##  "usrgrpid": "14",
            ##  "hostgroup_rights": [
            ##      {
            ##          "id": "19",
            ##          "permission": "3"
            ##      }
            ##  ]
            ## }
            #usergroups_with_rights = self.zapi.usergroup.get(
            #       userids = zabbix_user['zabbix_userid'],
            #       selectHostGroupRights = [ 'id', 'permission' ],
            #       output = 'usrgrpid',
            #)

            #hostgroups = []
            #for usergroup in usergroups_with_rights:
            #   for rights in usergroup['hostgroup_rights']:
            #       # Skip if we already have this hostgroup
            #       if rights['id'] in hostgroups:
            #           continue

            #       # Values for "permission" are:
            #       # - 0: access denied
            #       # - 2: read-only
            #       # - 3: read-write
            #       if int(rights['permission']) == 0:
            #           continue

            #       hostgroups.append(rights['id'])

            #hostgroups_with_hosts = self.zapi.hostgroup.get(
            #       groupids = hostgroups,
            #       selectHosts = [ 'hostid', 'name' ],
            #       output = [ 'groupid', 'name' ],
            #)

            #hosts_for_hostgroup = {}
            #for hostgroup in hostgroups_with_hosts:
            #   hosts = [ host['name'] for host in hostgroup['hosts'] ]
            #   hosts_for_hostgroup[hostgroup['name']] = hosts

            hosts_for_hostgroup = self.get_hostgroups_hosts_for_user(zabbix_user)

            reply = "You have access to these hosts:\n"

            for hostgroup in sorted(hosts_for_hostgroup):
                hosts = hosts_for_hostgroup[hostgroup]['hosts']

                reply += "\n<u>%s</u> (%s host(s))\n" % (hostgroup, len(hosts))
                reply += "\n".join(sorted([ host['name'] for host in hosts], key=str.casefold))
                reply += "\n"

            self.bot.reply_to(message, reply)



        @self.bot.message_handler(commands=['leftright'])
        def cmd_leftright(message):
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.row_width = 2
            keyboard.add(
                    telebot.types.InlineKeyboardButton("<<", callback_data="leftright left"),
                    telebot.types.InlineKeyboardButton(">>", callback_data="leftright right")
            )

            self.bot.reply_to(message, "Left... or right?", reply_markup = keyboard)


        @self.bot.callback_query_handler(func=lambda cb: cb.data.startswith('leftright '))
        def callback_leftright(cb):
            logging.debug("Callback: %s", cb)

            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.row_width = 2
            keyboard.add(
                    telebot.types.InlineKeyboardButton("<<", callback_data="leftright left"),
                    telebot.types.InlineKeyboardButton(">>", callback_data="leftright right")
            )

            cb.data = cb.data[10:]  # Cut off "leftright " prefix

            if cb.data == "left":
                new_message = cb.message.text + "\nLeft!"
                self.bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id, text=new_message, reply_markup = keyboard)
                self.bot.answer_callback_query(cb.id, "Left")
            elif cb.data == "right":
                new_message = cb.message.text + "\nRight!"
                self.bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id, text=new_message, reply_markup = keyboard)
                self.bot.answer_callback_query(cb.id, "Right")



        ### Graphs
        @self.bot.message_handler(commands=['graph'])
        def cmd_graph(message):
            zabbix_user = self.telegram_users[str(message.from_user.id)]
            hosts_for_hostgroup = self.get_hostgroups_hosts_for_user(zabbix_user)

            cust_hostgroups = { hostgroup: hosts for hostgroup, hosts in hosts_for_hostgroup.items() if (hostgroup.startswith('Customers/') and len(hosts) > 0) }

            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.row_width = 1

            for hostgroup in sorted(cust_hostgroups):
                hosts = cust_hostgroups[hostgroup]['hosts']

                keyboard.add(
                        telebot.types.InlineKeyboardButton(
                            hostgroup + " (" + str(len(hosts)) + " host(s))", callback_data="graph hostgroup " + cust_hostgroups[hostgroup]['id'])
                )

            self.bot.reply_to(message, "Choose a hostgroup.", reply_markup = keyboard)


        @self.bot.callback_query_handler(func=lambda cb: cb.data.startswith('graph hostgroup '))
        def callback_graph_select_host_from_hostgroup(cb):
            logging.debug("Callback: %s", cb)

            hostgroup_id = cb.data.split(' ')[2]
            hosts_zbx = self.zapi.host.get(
                    groupids = hostgroup_id,
                    selectGraphs = [ 'id' ],
                    selectHostGroups = [ 'groupid', 'name' ],
                    output = [ 'hostid', 'name' ],
            )

            hosts_with_graphcount = {}
            for host_zbx in hosts_zbx:
                hosts_with_graphcount[host_zbx['name']] = {
                        'id': host_zbx['hostid'],
                        'graphcount': len(host_zbx['graphs'])
                }

            new_text = 'Selected hostgroup: <b>%s</b>.\n\nPlease choose a host.' % hosts_zbx[0]['hostgroups'][0]['name']

            hosts_with_graphs = { host: data for host, data in hosts_with_graphcount.items() if data['graphcount'] > 0 }

            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.row_width = 1

            for host_with_graphs in sorted(hosts_with_graphs):
                host_data = hosts_with_graphs[host_with_graphs]

                keyboard.add(
                        telebot.types.InlineKeyboardButton(
                            host_with_graphs + " (" + str(host_data['graphcount']) + " graph(s))", callback_data="graph host " + host_data['id'])
                )

            self.bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id, text=new_text, reply_markup = keyboard)
            self.bot.answer_callback_query(cb.id, "You have selected hostgroup " + hosts_zbx[0]['hostgroups'][0]['name'])


        @self.bot.callback_query_handler(func=lambda cb: cb.data.startswith('graph host '))
        def callback_graph_select_graph_from_host(cb):
            logging.debug("Callback: %s", cb)

            host_id = cb.data.split(' ')[2]
            graphs_zbx = self.zapi.graph.get(
                    hostids = host_id,
                    selectHosts = [ 'name' ],
                    output = [ 'graphid', 'name' ],
            )

            new_text = 'Selected host: <b>%s</b>.\n\nPlease select a graph.' % graphs_zbx[0]['hosts'][0]['name']

            graphs = { graph['name']: { 'id': graph['graphid'] } for graph in graphs_zbx }

            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.row_width = 1

            for graph in sorted(graphs):
                graph_id = graphs[graph]['id']

                keyboard.add(telebot.types.InlineKeyboardButton(
                    graph, callback_data="graph graphid " + graph_id
                ))

            self.bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id, text=new_text, reply_markup=keyboard)
            self.bot.answer_callback_query(cb.id, "You have selected host " + graphs_zbx[0]['hosts'][0]['name'])


        @self.bot.callback_query_handler(func=lambda cb: cb.data.startswith('graph graphid '))
        def callback_graph_show_graph_with_graphid(cb):
            logging.debug("Callback: %s", cb)

            graph_id = cb.data.split(' ')[2]

            self.bot.send_chat_action(cb.message.chat.id, 'typing')

            graph = zabbix_frontend.get_graph(graph_id, 3600, 1200, 400)

            self.bot.send_photo(cb.message.chat.id, graph)
            self.bot.edit_message_text(chat_id=cb.message.chat.id, message_id=cb.message.message_id, text='Your graph is displayed', reply_markup=None)
            #self.bot.edit_message_media(chat_id=cb.message.chat.id, message_id=cb.message.message_id,media=graph,reply_markup=None)

            self.bot.answer_callback_query(cb.id, "Your graph should be there")






            #zapi.url.removesuffix('api_jsonrpc.php')



        ### Sst, easter egg :)
        @self.bot.message_handler(commands=['💩'])
        def cmd_pile_of_poo(message):
            self.bot.reply_to(message, "ZBXHIT is da shit!")



        ### Fallback handler - unknown command
        @self.bot.message_handler(func=lambda message: True)
        def fallback_handler(message):
            self.bot.reply_to(message, "Unknown command %s. Try /help." % message.text)



    #######################################################################
    # Helper functions
    #######################################################################
    def get_hostgroups_hosts_for_user(self, zabbix_user):
        hostgroups = []

        if zabbix_user['is_superadmin']:
            # Super admins have implicit access to all hostgroups.
            # Unfortunately the logic used for non-superadmins below
            # doesn't work here: using selectHostGroupRights only returns
            # the hostgroups where explicit rights have been assigned
            # to the user.
            all_hostgroups = self.zapi.hostgroup.get(
                    output = [ 'groupid' ],
            )

            hostgroups = [ group['groupid'] for group in all_hostgroups ]
        else:
            # Result in an array of these:
            # {
            #   "usrgrpid": "14",
            #   "hostgroup_rights": [
            #       {
            #           "id": "19",
            #           "permission": "3"
            #       }
            #   ]
            # }
            usergroups_with_rights = self.zapi.usergroup.get(
                    userids = zabbix_user['zabbix_userid'],
                    selectHostGroupRights = [ 'id', 'permission' ],
                    output = 'usrgrpid',
            )

            for usergroup in usergroups_with_rights:
                for rights in usergroup['hostgroup_rights']:
                    # Skip if we already have this hostgroup
                    if rights['id'] in hostgroups:
                        continue

                    # Values for "permission" are:
                    # - 0: access denied
                    # - 2: read-only
                    # - 3: read-write
                    if int(rights['permission']) == 0:
                        continue

                    hostgroups.append(rights['id'])

        hostgroups_with_hosts = self.zapi.hostgroup.get(
                groupids = hostgroups,
                selectHosts = [ 'hostid', 'name' ],
                output = [ 'groupid', 'name' ],
        )

        hosts_for_hostgroup = {}
        for hostgroup in hostgroups_with_hosts:
            hosts = [ { 'id': host['hostid'], 'name': host['name'] } for host in hostgroup['hosts'] ]

            hosts_for_hostgroup[hostgroup['name']] = {
                    'id': hostgroup['groupid'],
                    'hosts': hosts,
            }

        logging.debug("--- Hosts for hostsgroup: %s", hosts_for_hostgroup)

        return hosts_for_hostgroup



    def start_polling(self):
        self.bot.infinity_polling()
