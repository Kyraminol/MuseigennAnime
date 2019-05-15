(function($){
  $(function(){
    var $handlersTab = $('#handlers-tab');
    var $handlersShortcuts = $('.handler-shortcut-open');

    var $searchRow = $('#search-row');
    var $searchDiv = $('#search-div');
    var $searchInput = $('#search-input');
    var $searchAllSwitch = $('#search-all-switch');
    var $searchAllLoading = $('#search-all-loading');
    var search_lookup = {};

    var $settingsTheme = $('#settings-theme');
    var $settingsSave = $('#settings-save');
    var $settingsShutdown = $('#settings-shutdown');
    var $shutdownModal = $('#shutdown-modal');
    var $shutdownConfirm = $('#shutdown-confirm');

    var $settingsModal = $('#settings-modal');
    var $settingsTabs = $('#settings-tabs');
    var $settingsAdvancedSwitch = $('#settings-advanced-switch');
    var $settingsAdvancedLi = $('#settings-advanced-li');
    var $settingsThemesReload = $('#settings-reload-themes');
    var $settingsDownloadPath = $('#settings-download-path');
    var $settingsDownloadManagerMax = $('#settings-download-manager-max');
    var $settingsModulesTbody = $('#settings-modules-tbody');

    var $downloadModal = $('#download-modal');
    var $downloadModalContent = $('#download-modal-content');
    var $downloadModelLoading = $('#download-modal-loading');
    var $downloadModalDevice = $('#download-modal-device');
    var $downloadModalDeviceSwitch = $('#download-modal-device-switch');
    var $downloadDownload = $('#download-download');

    var $downloadManagerModal = $('#download-manager-modal');
    var $downloadManagerModalTable = $('#download-manager-modal-table');
    var $downloadManagerModalTitle = $('#download-manager-modal-title');
    var $downloadManagerModalClean = $('#download-manager-modal-clean');
    var $downloadManagerModalCancelAll = $('#download-manager-modal-cancel-all');

    var dmSocket = undefined;
    var dsSocket = undefined;
    var ds_retrieved = [];

    var $sidenav = $('#sidenav');


    $handlersTab.tabs();
    $settingsTabs.tabs();

    $sidenav.sidenav();

    $handlersShortcuts.on('click', function(e){
      e.preventDefault();
      var $this = $(this);
      $handlersTab.tabs('select', 'nav-handler-' + $this.data('handler'));
    });

    $searchInput.autocomplete({
      onAutocomplete: function(val){
        var ids = search_lookup[val];
        $handlersTab.tabs('select', 'nav-handler-' + ids[1]);
        var $el = $('#nav-handler-' + ids[1] + ' div > ul > li').filter(function(){
          var $this = $(this);
          var result = false;
          $.each($this.data('anime_list'), function(){
            if(this[1] === ids[0]){
              result = true;
            }
          });
          return result;
        });
        $el.click();
        var index = 0;
        $.each($el.data('anime_list'), function(i){
          if(this[1] === ids[0]){
            index = i;
          }
        });
        var $ul = $('#pagination-' + ids[1] + '-' + $el.data('index'));
        $ul.collapsible('open', index);
        $ul.find(':nth-child(' + (index+1) + ')').get(0).scrollIntoView({behavior: 'smooth'});
      },
    });
    var searchColorize = function(){
      $searchDiv.find('li > span').addClass(theme['index_list_header']).addClass(theme['index_list_header_text']).find('span').addClass(theme['index_list_header_text']);
    };
    $searchInput.on('keyup', function(){
      $searchInput.autocomplete('open');
      searchColorize();
    });
    $searchInput.on('focus', function(){
      setTimeout(searchColorize, 100);
    });
    $searchInput.click(function(){
      setTimeout(searchColorize, 100);
    });
    $searchAllSwitch.on('change', function(){
      if(this.checked){
        $searchInput.attr('disabled', true);
        $searchAllLoading.removeClass('hide');
        var $lis = $handlersTab.find('li:not(.default-tab,.indicator)');
        $.each($lis, function(){
          var $this = $(this);
          load_handler_tab($this, function($el, total){
            var temp = $searchInput.data('temp');
            if(!temp){
              temp = {
                data: {},
                lookup: {},
                loaded: 0
              }
            }
            $.each($el.data('autocomplete_data'), function(key){
              temp['data'][key + ' (' + $el.text().trim() + ')'] = null;
            });
            $.each($el.data('autocomplete_lookup'), function(key, value){
              temp['lookup'][key + ' (' + $el.text().trim() + ')'] = value;
            });
            temp['loaded']++;
            if(temp['loaded'] === total){
              $searchInput.data({temp: undefined});
              $searchInput.autocomplete('updateData', temp['data']);
              search_lookup = temp['lookup'];
              $searchInput.attr('disabled', false);
              $searchAllLoading.addClass('hide');
            }else{
              $searchInput.data({temp: temp});
            }
          }, $lis.length);
        });
      }else{
        var $el = $(M.Tabs.getInstance($handlersTab.get(0)).$activeTabLink.parent());
        load_handler_tab($el, update_search);
      }

    });

    $settingsModal.modal({
      onOpenEnd: function(){
        if($settingsAdvancedSwitch.get(0).checked){
          $settingsAdvancedLi.removeClass('hide');
        }
        $settingsTabs.tabs('updateTabIndicator');
      }
    });
    $shutdownModal.modal();

    $downloadModal.modal({
      onCloseEnd: function(){
        $downloadModalContent.empty();
        $downloadModelLoading.removeClass('hide');
        $downloadModalDevice.addClass('hide');
      }
    });

    var cancelDownloads = function($trs){
      var paths = [];
      $trs.each(function(){
        paths.push($(this).data('path'));
      });
      dmSocket.emit("cancel", {paths: paths}, function(){
        $trs.each(function(){
          var $tr = $(this);
          var $tds = $tr.find('td');
          $($tds.get(3)).text(strings['cancelled']);
          $($tds.get(4)).text('');
          $($tds.get(5)).text('');
          $($tds.get(6)).text('');
          $($tds.get(7)).empty();
        });
      });
    };

    $downloadManagerModalCancelAll.on('click', function () {
      cancelDownloads($downloadManagerModalTable.find('tbody').find('tr:has(td:has(a))'))
    });

    $downloadManagerModalClean.on('click', function () {
      $downloadManagerModalTable.find('tbody').empty();
      dmSocket.emit('clean');
    });

    var downloadManagerOpen = function () {
      dmSocket = io.connect('http://' + document.domain + ':' + location.port + '/downloads');
      dmSocket.on("status",function(event) {
        var $tbody = $downloadManagerModalTable.find('tbody');
        var stats = {downloading: 0, finished: 0, queued: 0};
        $.each(event, function(path, values){
          var info = values['info'];
          var status = values['status'];
          var $tr = $tbody.find("tr").filterByData('path', path); // TODO: remove filterByData dependency
          var perc = (status['downloaded_bytes'] * 100 / status['total_bytes_estimate']).toFixed(1);
          if($tr.length === 0){
            $tr = $('<tr class="download-manager-row"></tr>');
            $tr.data({path: path, values: values});
            var $tdCancel = $('<td></td>');
            var $aCancel = $('<a href="#"><i class="material-icons left ' + theme['index_body_text'] + '">cancel</i></a>');
            $aCancel.click(function(){
              cancelDownloads($(this).parents('tr.download-manager-row'))
            });
            $tdCancel.append($aCancel);
            var title = '';
            if(info['episode_title'] !== undefined){
              title = info['episode_title']
            }
            $tr.append('<td>' + info['anime_name'] + '</td><td>' + info['episode_n'] + '</td><td>' + title + '</td><td class="capitalize"></td><td></td><td></td><td></td>');
            $tr.append($tdCancel);
            $tbody.append($tr);
          }
          var oldValues = $tr.data('values');
          var $tds = $tr.find('td');

          switch(status['status']){
            case 'downloading':
              $($tds.get(3)).text(strings['downloading']);
              if (perc > oldValues['status']['perc']) {
                $($tds.get(4)).text(perc + '%');
              }
              $($tds.get(5)).text(status['_speed_str']);
              $($tds.get(6)).text(status['_eta_str']);
              stats['downloading']++;
              break;
            case 'finished':
              $($tds.get(3)).text(strings['finished']);
              $($tds.get(4)).text('100%');
              $($tds.get(5)).text('');
              $($tds.get(6)).text('');
              $($tds.get(7)).empty();
              stats['finished']++;
              break;
            case 'cancelled':
              $($tds.get(3)).text(strings['cancelled']);
              $($tds.get(4)).text('');
              $($tds.get(5)).text('');
              $($tds.get(6)).text('');
              $($tds.get(7)).empty();
              break;
            case 'queued':
              $($tds.get(3)).text(strings['queued']);
              stats['queued']++;
              break;
            default:
              $($tds.get(3)).text(status['status']);
          }

          values['status']['perc'] = perc;
          $tr.data('values', values);
        });
        $downloadManagerModalTitle.text(strings['download_manager_downloads'].format(stats['downloading'], stats['finished'], stats['queued']));
        if(Object.keys(event).length > 0){
          $downloadManagerModalTable.removeClass('hide');
          $downloadManagerModalClean.removeClass('hide');
          $downloadManagerModalCancelAll.removeClass('hide');
        } else {
          $downloadManagerModalTable.addClass('hide');
          $downloadManagerModalClean.addClass('hide');
          $downloadManagerModalCancelAll.addClass('hide');
        }
        dmSocket.emit("ACK");
      });
    };

    var downloadManagerClose = function () {
      dmSocket.disconnect();
      dmSocket = undefined;
    };

    $downloadManagerModal.modal({
      onOpenStart: downloadManagerOpen,
      onCloseStart: downloadManagerClose
    });

    $settingsAdvancedSwitch.on('change', function(){
      if(this.checked){
        $settingsAdvancedLi.removeClass('hide');
      }else{
        $settingsAdvancedLi.addClass('hide');
      }
      $settingsTabs.tabs('updateTabIndicator');
    });

    $settingsTheme.formSelect();
    $settingsTheme.parent().find('input').addClass(theme['index_body_text']).parent().find('li').addClass(theme['index_body_main']).find('span').addClass(theme['index_body_text']);

    $settingsShutdown.click(function(){
      $settingsModal.modal('close');
      $shutdownModal.modal('open');
    });

    $shutdownConfirm.click(function () {
      $.ajax({
        url: '/api/v1/shutdown',
        type: 'POST'
      })
    });

    var load_handler_tab = function($el, callback, callback_argument){
      if($el.hasClass('loaded') === false) {
        $el.addClass('loaded');
        var handler_id = $el.attr('id').substr(12);
        $.ajax({
          url: '/api/v1/anime/' + handler_id,
          success: function (data) {
            var $divHandler = $('#nav-handler-' + handler_id);
            var $pagination = $divHandler.find('ul.pagination');
            var $div = $pagination.parent().after('<div class="row"></div>').next();
            $divHandler.find('.preloader-panel').addClass('hide');
            var index = 0;
            var autocomplete_data = {};
            var autocomplete_lookup = {};
            $.each(data, function (char, anime_list) {
              $.each(anime_list, function (i, anime) {
                autocomplete_data[anime[0]] = null;
                autocomplete_lookup[anime[0]] = [anime[1], anime[2]];
              });
              var $li = $('<li class="waves-effect"><a class="' + theme['index_pagination_main'] + ' ' + theme['index_pagination_text'] + '">' + char.toUpperCase() + '</a></li>');
              $li.data({anime_list: anime_list, index: index, handler: handler_id});
              $li.on('click', pagination);
              $pagination.append($li);
              $div.append('<ul id="pagination-' + handler_id + '-' + index + '" class="collapsible popout hide"></ul>');
              index++;
            });
            $el.data({
              autocomplete_data: autocomplete_data,
              autocomplete_lookup: autocomplete_lookup,
              handler: handler_id
            });
            $handlersTab.tabs('updateTabIndicator');
            callback($el, callback_argument);
          },
          error: function () {
            $el.removeClass('loaded');
            // TODO: add error
          },

        })
      } else {
        callback($el, callback_argument);
      }
    };

    var update_search = function($el){
      if(!$searchAllSwitch.get(0).checked){
        $searchInput.autocomplete('updateData', $el.data('autocomplete_data'));
        search_lookup = $el.data('autocomplete_lookup');
      }
    };

    $handlersTab.find('.tab').on("click", function(ev){
      ev.preventDefault();
      var $this = $(this);
      if($this.hasClass('default-tab')){
        $searchRow.addClass('hide');
      } else {
        $searchRow.removeClass('hide');
        load_handler_tab($this, update_search);
      }
    });

    var pagination = function(){
      var $this = $(this);
      var $old = $this.parent().find('li.active');
      if($old.length > 0){
        $old.removeClass('active ' + theme['index_pagination_active_main'] + ' ' + theme['index_pagination_active_text']);
        $old.addClass(theme['index_pagination_main'] + ' ' + theme['index_pagination_text']);
        var $div = $('#pagination-' + $old.data('handler') + '-' + $old.data('index'));
        $div.addClass('hide');
        $div.collapsible('close', $div.find('li.anime.active').index());
      }
      $this.addClass('active ' + theme['index_pagination_active_main'] + ' ' + theme['index_pagination_active_text']);
      $this.removeClass(theme['index_pagination_main'] + ' ' + theme['index_pagination_text']);
      var $ul = $('#pagination-' + $this.data('handler') + '-' + $this.data('index'));
      if($ul.hasClass('loaded') === false){
        $ul.addClass('loaded');
        $.each($this.data('anime_list'), function(){
          var $li = $('<li class="anime ' + theme['index_list_body'] + '"><div class="collapsible-header ' + theme['index_list_header'] + ' ' + theme['index_list_header_text'] + '">' + this[0] + '</div><div class="collapsible-body white-text"><div class="center-align info-loading">' + strings['loading'] + '<div class="progress"><div class="indeterminate ' + theme['index_list_loading'] + '"></div></div></div></div></li>');
          $li.data({name: this[0], anime_id: this[1], handler_id: this[2]});
          $ul.append($li);
        });
        $ul.collapsible({
          onOpenStart: load_info,
        });


      }
      $ul.removeClass('hide');
      $handlersTab.tabs('updateTabIndicator');
    };

    var load_info = function(el){
      var $el = $(el);
      if($el.hasClass('loaded')){
        return
      }
      $el.addClass('loaded');
      var el_data = $el.data();
      var $parent_body = $el.find('.collapsible-body');
      var $info_loading = $parent_body.find('.info-loading');
      $.ajax({
        url: '/api/v1/anime/' + el_data['handler_id'] + '/' + el_data['anime_id'],
        success: function(response){
          if(response['result'] === 'ok'){
            var data = response['data'];
            var $ul = $('<ul class="collapsible expandable z-depth-0" style="border:0"></ul>');
            $.each(data, function (key, value) {
              if(key.substring(0,1) === '_'){
                return true;
              }
              key = key.replace('_', ' ');
              var $li = $('<li></li>');
              var $header = $('<div class="collapsible-header ' + theme['index_list_info_header'] + ' capitalize"></div>');
              var $body = $('<div class="collapsible-body ' + theme['index_list_info_body'] + '"></div>');
              var $headerDiv = $('<div class="info-header ' + theme['index_list_info_header_text'] + '"></div>');
              var $bodyDiv = $('<div class="info-body ' + theme['index_list_info_body_text'] + '"></div>');

              $headerDiv.text(key);
              if (typeof value === 'object') {
                var $table = $('<table class="highlight capitalize"></table>');
                var $tbody = $('<tbody></tbody>');
                var n = 0;
                var valueLenght = Object.keys(value).length;
                $.each(value, function (k, v) {
                  n += 1;
                  var $tr = $('<tr></tr>');
                  if (n === valueLenght) {
                    $tr.addClass('no-border-bottom');
                  }
                  var $td1 = $('<td></td>').text(k);
                  var $td2 = $('<td></td>').text(v);
                  $tr.append($td1);
                  $tr.append($td2);
                  $tbody.append($tr);
                });
                $table.append($tbody);
                $bodyDiv.append($table);
              } else {
                $bodyDiv.text(value)
              }
              $header.append($headerDiv);
              $body.append($bodyDiv);
              $li.append($header);
              $li.append($body);
              $ul.append($li);
            });
            if(data['_available'] === false){
              $parent_body.append('<h4 class="center-align">' + strings['error_loading_info_not_available'] + '</h4>')
            } else {
              var $bodyButtons = $('<div class="row"></div>');
              var $watchButtonLarge = $('<a href="#" class="left btn hide-on-small-and-down btn-large waves-effect ' + theme['index_list_button'] + ' ' + theme['index_list_button_text'] + '"><i class="material-icons left">visibility</i>' + strings['watch'] + '</a>');
              var $watchButton = $('<a href="#" class="left btn hide-on-med-and-up waves-effect ' + theme['index_list_button'] + ' ' + theme['index_list_button_text'] + '"><i class="material-icons left">visibility</i>' + strings['watch'] + '</a>');
              var $downloadButtonLarge = $('<a href="#" class="right btn hide-on-small-and-down btn-large waves-effect ' + theme['index_list_button'] + ' ' + theme['index_list_button_text'] + '"><i class="material-icons left">file_download</i>' + strings['download'] + '</a>');
              var $downloadButton = $('<a href="#" class="right btn hide-on-med-and-up waves-effect ' + theme['index_list_button'] + ' ' + theme['index_list_button_text'] + '"><i class="material-icons left">file_download</i>' + strings['download'] + '</a>');
              $bodyButtons.append($watchButton);
              $bodyButtons.append($watchButtonLarge);
              $bodyButtons.append($downloadButton);
              $bodyButtons.append($downloadButtonLarge);
              $watchButton.data(el_data);
              $watchButtonLarge.data(el_data);
              $downloadButton.data(el_data);
              $downloadButtonLarge.data(el_data);
              $watchButton.on('click', watch_button);
              $watchButtonLarge.on('click', watch_button);
              $downloadButton.on('click', download_button);
              $downloadButtonLarge.on('click', download_button);
              $parent_body.append($bodyButtons);
            }
            $info_loading.addClass('hide');
            $parent_body.prepend($ul);

            $ul.collapsible({accordion: false})
          } else {
            $info_loading.addClass('hide');
            $parent_body.append('<h4 class="center-align">' + strings['error_loading_info_not_available'] + '</h4>')
          }
        },
        error: function(error){
          $el.removeClass('loaded');
          // TODO: add error
        }
      })

    };

    var watch_button = function(e){
      e.preventDefault();
      var $this = $(this);
      var data = $this.data();
      $.redirect('/player', {handler_id: data['handler_id'], anime_id: data['anime_id']},'GET', '_blank');
    };

    var downloadCheckAll = function(){
      var $el = $(this);
      var $inputs = $el.parents('table.download-table').find('td > label > input');
      if($el.prop('checked')){
        $inputs.prop('checked', true);
      } else {
        $inputs.prop('checked', false);
      }
    };

    var download_button = function(e){
      e.preventDefault();
      var $this = $(this);
      var button_data = $this.data();
      var handler_id = button_data['handler_id'];
      var anime_id = button_data['anime_id'];
      $downloadModal.modal('open');
      $.ajax({
        url: '/api/v1/anime/download/' + handler_id + '/' + anime_id,
        success: function(data){
          if(data['result'] === 'ok'){
            $downloadModelLoading.addClass('hide');
            $downloadModalDevice.removeClass('hide');
            $downloadModalContent.empty();
            var $ul = $('<ul class="collapsible"></ul>');
            $.each(data['data'], function(index, data){
              var season_id = data['season_id'];
              var $li = $('<li></li>');
              var $header = $('<div class="collapsible-header ' + theme['index_list_header'] + ' ' + theme['index_list_header_text'] + '">' + data['season_name'] + '</div>');
              var $body = $('<div class="collapsible-body"></div>');
              var $table = $('<table class="highlight download-table"></table>');
              var $thead = $('<thead><tr><th>'+ strings['episode'] +'</th></tr></thead>');
              var $checkboxHead = $('<th><label><input type="checkbox" class="filled-in check-all"/><span></span></label></th>');
              var $tbody = $('<tbody></tbody>');
              $.each(data['episodes'], function(i, episode){
                if(episode['video_url'] === null){
                  return true;
                }
                var $tr = $('<tr></tr>');
                if(i === data['episodes'].length - 1){
                  $tr.addClass('no-border-bottom');
                }
                var episode_title = strings['episode'] + ' ';
                if('episode_number' in episode){
                  episode_title = episode_title + episode['episode_number']
                }else{
                  episode_title = episode_title + ("0" + episode['episode_id']).slice(-2);
                }
                if('episode_title' in episode){
                  if(episode_title !== episode['episode_title']){
                    if(episode['episode_title'].includes(episode_title)) {
                      episode_title = episode['episode_title'];
                    }else{
                      episode_title = episode_title + ' - ' + episode['episode_title'];
                    }
                  }
                }

                var $checkbox = $('<td><label><input type="checkbox" class="filled-in"/><span></span></label></td>');
                var $episode = $('<td>' + episode_title + '</td>');
                $checkbox.find('input').data({
                  handler_id: handler_id,
                  anime_id: anime_id,
                  season_id: season_id,
                  episode_id: episode['episode_id']
                });
                $tr.append($checkbox);
                $tr.append($episode);
                $tbody.append($tr);
              });
              $thead.find('tr').prepend($checkboxHead);
              $table.append($thead);
              $table.append($tbody);
              $body.append($table);
              $li.append($header);
              $li.append($body);
              $ul.append($li);
            });
            $ul.find('.check-all').click(downloadCheckAll);
            $ul.collapsible();
            $downloadModalContent.append($ul);
          }



        },
        error: function(){
          // TODO: add error
        },
      });
    };

    $downloadDownload.on('click', function(){
      var $inputs = $downloadModalContent.find('input:checked:not(".check-all")');
      var device_switch = $downloadModalDeviceSwitch.get(0).checked;
      var data = [];
      $.each($inputs, function(index, input){
        var input_data = $(input).data();
        data.push({
          handler_id: input_data['handler_id'],
          anime_id: input_data['anime_id'],
          season_id: input_data['season_id'],
          episode_id: input_data['episode_id']})
      });
      $.ajax({
        url: '/api/v1/downloads',
        type: 'POST',
        data: {episodes: JSON.stringify(data), stream_download: device_switch},
        success: function(response){
          if(response['result'] === 'ok'){
            M.toast({html: response['data'], classes: theme['index_nav_main'] + ' ' + theme['index_nav_text']});
            if(device_switch){
              dsSocket = io.connect('http://' + document.domain + ':' + location.port + '/download');
              dsSocket.on('serve',function(event) {
                if(!ds_retrieved.includes(event)){
                  ds_retrieved.push(event);
                  console.log(ds_retrieved);
                  window.location = '/api/v1/download/' + event;
                }
              });
            }
          }
        }

      })
    });

    $settingsThemesReload.on('click', function(){
      $.ajax({
        url: '/api/v1/themes',
        success: function(data){
          if(data["result"] === "ok"){
            $settingsTheme.empty();
            $.each(data['data'], function(key, value) {
              var name = strings['settings_theme_no_name'];
              var author = strings['settings_theme_no_author'];
              var selected = "";
              if(value['THEME_NAME']){
                name = value['THEME_NAME'];
              }
              if(value['THEME_AUTHOR']){
                author = value['THEME_AUTHOR'];
              }
              if(theme['__theme_folder__'] === key) {
                selected = 'selected';
              }
              var $option = $('<option value="' + key + '" ' + selected + '>' + name + ' (' + author + ')</option>');
              $settingsTheme.append($option);
            });
            $settingsTheme.formSelect();
            $settingsTheme.parent().find('input').addClass(theme['index_body_text']).parent().find('li').addClass(theme['index_body_main']).find('span').addClass(theme['index_body_text']);
          }

        }
      })
    });

    $settingsSave.on('click', function(e){
      e.preventDefault();
      $settingsTheme.formSelect();
      $settingsTheme.parent().find('input').addClass(theme['index_body_text']).parent().find('li').addClass(theme['index_body_main']).find('span').addClass(theme['index_body_text']);
      var new_theme = $settingsTheme.formSelect('getSelectedValues')[0];
      var download_path = $settingsDownloadPath.val();
      var download_manager_max = $settingsDownloadManagerMax.val();
      var settings_advanced_switch = $settingsAdvancedSwitch.get(0).checked;
      var $handlers = $settingsModulesTbody.find("input");
      var handlers = {};
      $.each($handlers, function(){
        var status = false;
        if(this.checked){
          status = true;
        }
        handlers[$(this).data('handler')] = status;
      });
      $.ajax({
        url: '/settings',
        type: 'POST',
        data: {
          THEME: new_theme,
          DOWNLOAD_PATH: download_path,
          DOWNLOAD_MANAGER_MAX_DOWNLOADS: download_manager_max,
          SETTINGS_ADVANCED_SWITCH: settings_advanced_switch,
          HANDLERS: JSON.stringify(handlers),
        },
        success: function(){
          location.reload();
        }
      })
    });

  });
})(jQuery);