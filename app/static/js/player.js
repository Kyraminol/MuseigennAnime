(function($){
  $(function(){
    var $sidenav = $('.sidenav');
    var $sidenavTrigger = $('.sidenav-trigger');
    var $collapsible = $('.collapsible');
    $sidenav.sidenav();
    $sidenav.sidenav('open');
    $collapsible.collapsible();

    if($collapsible.length === 1){
      $collapsible.collapsible('open');
    }



    var $episodeName = $('#episode-name');
    var $episodeNameDiv = $('#episode-name-div');
    var $episodePrev = $('#episode-prev');
    var $episodeNext = $('#episode-next');
    var $anime_id = $('#anime-id');
    var $handler_id = $('#handler-id');
    var $episode_id = $('#episode-id');
    var $player = $('#player');
    var $playerVideo = $('#player-video');
    var $playerIframe = $('#player-iframe');
    var $playerOverlay = $('#player-overlay');
    var $playerLoading = $('#player-loading');
    var $lightsoff = $('#lights-off');
    var $dim = $('#dim-lights-div');
    var $copyrightContainer = $('.footer-copyright > .container');
    var season_prefix = "#season-";
    var season_class = ".season";
    var episode_prefix = "#episode-";
    var episode_class = ".episode";
    var first_load = false;
    var classes = {};
    var re_ext = /(?:\.([^.]+))?$/;
    var re_yt = /youtube/;


    $lightsoff.click(function () {
      if($dim.css('display') === 'none') {
        classes = {
          lightsOff: $lightsoff.attr('class'),
          copyrightContainer: $copyrightContainer.attr('class'),
          episodePrev: $episodePrev.find('i.show-on-dim').attr('class'),
          episodeNext: $episodeNext.find('i.show-on-dim').attr('class'),
          sidenavTrigger: $sidenavTrigger.attr('class')
        };
        $dim.fadeIn(250);
        $lightsoff.attr('class', 'show-on-dim white-text');
        $copyrightContainer.attr('class', 'container show-on-dim white-text');
        $episodePrev.find('i.show-on-dim').attr('class', 'material-icons left show-on-dim white-text');
        $episodeNext.find('i.show-on-dim').attr('class', 'material-icons right show-on-dim white-text');
        $sidenavTrigger.attr('class', 'sidenav-trigger show-on-large show-on-dim white-text');
      } else {
        $dim.fadeOut(500);
        $lightsoff.attr('class', classes['lightsOff']);
        $copyrightContainer.attr('class', classes['copyrightContainer']);
        $episodePrev.find('i.show-on-dim').attr('class', classes['episodePrev']);
        $episodeNext.find('i.show-on-dim').attr('class', classes['episodeNext']);
        $sidenavTrigger.attr('class', classes['sidenavTrigger']);
      }
    });


    $('a.episode').click(function(){
      var $el = $(this);
      var episode_id = $el.attr('id');
      episode_load(episode_id.slice(episode_prefix.length - 1));
    });

    $episodePrev.click(function(){
      episode_load(episode_get_prev())
    });

    $episodeNext.click(function(){
      episode_load(episode_get_next())
    });

    var episode_get_prev = function(){
      var episode_id = $episode_id.text();
      var $prev = $sidenav.find(episode_prefix + episode_id + episode_class).parent().prev().find('a');
      if($prev.length === 0){
        return undefined
      }
      return $prev.attr('id').slice(episode_prefix.length - 1);
    };

    var episode_get_next = function(){
      var episode_id = $episode_id.text();
      var $next = $sidenav.find(episode_prefix + episode_id + episode_class).parent().next().find('a');
      if($next.length === 0){
        return undefined
      }
      return $next.attr('id').slice(episode_prefix.length - 1);
    };


    var episode_load = function(episode_id, play){
      var handler_id = $handler_id.text();
      var anime_id = $anime_id.text();
      var season_id = $sidenav.find(episode_prefix + episode_id + episode_class).parents('li' + season_class).attr('id').slice(season_prefix.length - 1);

      $player.addClass('hide');
      $playerVideo.addClass('hide');
      $playerIframe.addClass('hide');
      $playerLoading.removeClass('hide');
      $lightsoff.addClass('hide');
      $episodeNameDiv.addClass('hide');
      $episodePrev.addClass('hide');
      $episodeNext.addClass('hide');
      $sidenav.sidenav('close');

      $.ajax({
        url: '/api/v1/anime/' + handler_id + '/' + anime_id + '/' + season_id + '/' + episode_id,
        type: 'GET',
        success: function(data){
          console.log(data);
          if('video_url' in data) {
            var ext = re_ext.exec(data['video_url'])[1];
            if (ext === 'm3u8' || data['video_type'] === 'video/hls') {
              if (Hls.isSupported()) {
                var config = {
                  xhrSetup: function(xhr, url) {
                    xhr.withCredentials = true;
                  }
                };
                var video = $playerVideo.get(0);
                var hls = new Hls(config);
                hls.loadSource(data['video_url']);
                hls.attachMedia(video);
                $playerVideo.removeClass('hide');
              } else {
                M.toast({html: strings['hls_not_supported']});
              }
            } else if (ext === 'mp4') {
              $playerVideo.find('source').attr('src', data['video_url']);
              $playerVideo.find('source').attr('type', 'video/mp4');
              $playerVideo.get(0).load();
              $playerVideo.removeClass('hide');
            } else if (re_yt.test(data['video_url']) === true) {
              $playerIframe.attr('src', data['video_url'].replace(/watch\?v=/i, 'embed/'));
              $playerIframe.removeClass('hide');
            }
            $episode_id.text(episode_id);
            if (episode_get_prev() !== undefined) {
              $episodePrev.removeClass('hide');
            }
            if (episode_get_next() !== undefined) {
              $episodeNext.removeClass('hide');
            }
            var title = '';
            if ('episode_number' in data) {
              title = strings['episode'] + ' ' + data['episode_number'];
            }
            if ('episode_title' in data) {
              if (title !== '') {
                title = title + ' - '
              }
              title = title + data['episode_title'];
            }
            if (title === '') {
              title = strings['episode'] + ' ' + episode_id;
            }
            $episodeName.text(title);
            $player.removeClass('hide');
            $lightsoff.removeClass('hide');
            $episodeNameDiv.removeClass('hide');
            $playerLoading.addClass('hide');
            if (first_load === false) {
              $playerVideo.on('ended', video_end);
              first_load = true;
            }
            if (play === true) {
              $playerVideo.get(0).play()
            }
          } else if('availability_date' in data){
            // TODO
          } else {
            M.toast({html: strings['error_loading_episode'], classes: 'red'})
          }
        },
        error: function(request, status, error){
          var text = strings['error_loading_episode'] + ': "' + status;
          if(error){
            text += ': ' + error;
          }
          text += '"';
          M.toast({html: text, classes: 'red'})
        }
      });
    };

    var video_end = function(){
      $playerVideo.get(0).pause();
      var next = episode_get_next();
      if(next) {
        var timeouts = [];
        for (var i = 0; i <= 11; i++) {
          var timeout = setTimeout(function (i) {
            if (i === 11) {
              $playerOverlay.addClass('hide');
              episode_load(next, true);
            }
            bar.animate(i * 0.1);
            if(i === 1){
              $playerOverlay.removeClass('hide');
            }
          }, i * 1000, i);
          timeouts.push(timeout);
        }
        $(document).click(function(){
          for (var i = 0; i < timeouts.length; i++) {
            clearTimeout(timeouts[i]);
          }
          $playerOverlay.addClass('hide');
          $(document).unbind('click');
        })
      }
    };


    var bar = new ProgressBar.Circle('#player-overlay', {
      color: '#aaa',
      strokeWidth: 10,
      trailWidth: 2,
      easing: 'easeInOut',
      duration: 900,
      text: {
        autoStyleContainer: false
      },
      svgStyle: {
        position: 'relative',
        display: 'block',
        width: '20%',
        height: '20%',
        margin: '0',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)'
      },
      from: { color: '#fff', width: 10 },
      to: { color: '#fff', width: 10 },
      step: function(state, circle) {
        circle.path.setAttribute('stroke', state.color);
        circle.path.setAttribute('stroke-width', state.width);

        var value = Math.round(circle.value() * 10);
        circle.setText(10 - value);

      }
    });
    bar.text.style.fontSize = '3rem';
    var $text = $('<div><p>' + strings['autoplaying'] + '</p><p>' + strings['click_anywhere_cancel'] + '</p></div>');
    $playerOverlay.append($text);


  });
})(jQuery);