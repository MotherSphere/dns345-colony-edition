var MODULE_SORT_LIST = new Array();		
var MIIICASA_FLAG = 0;

/*
APP_INFO[x][0] = module name
APP_INFO[x][1] = icon name(id)
APP_INFO[x][2] = url
APP_INFO[x][3] = show name
APP_INFO[x][4] = enable/disable
APP_INFO[x][5] = element id
APP_INFO[x][6]= module type,ex: 1 -> application 2-> add-ons
APP_INFO[x][7] = xxx_display.png status,ex:0-> don't exist,show default icon; 1->exist
APP_INFO[x][8] = xxx_on.png,ex:0-> don't exist,show default icon; 1->exist
APP_INFO[x][9] = xxx_off.png,ex:0-> don't exist,show default icon; 1->exist
*/		
var APP_INFO  = new Array();
APP_INFO[0] = new Array("schedule_downloads","icon_schedule_downloads","/web/index.html?id=schedule_downloads",_T('_menu','ftp_http_downloads'),"1",_T('_menu','ftp_http_downloads'),"1","1","1","1");
APP_INFO[1] = new Array("remote_backup","icon_remote_backup","/web/backup_mgr/remote_main.html",_T('_menu','remote_backups'),"1",_T('_menu','remote_backups'),"1","1","1","1");
APP_INFO[2] = new Array("schedule_backups","icon_schedule_backups","/web/index.html?id=schedule_backups",_T('_menu','schedule_backups'),"1",_T('_menu','schedule_backups'),"1","1","1","1");
APP_INFO[3] = new Array("p2p","icon_p2p","/web/index.html?id=p2p",_T('_menu','p2p_downloads'),"1",_T('_menu','p2p_downloads'),"1","1","1","1");
APP_INFO[4] = new Array("webfile","icon_webfile","/web/web_file/web_file_server.html",_T('_menu','web_file_server'),"1",_T('_menu','web_file_server'),"1","1","1","1");
APP_INFO[5] = new Array("amazon_s3","icon_amazon_s3","/web/backup_mgr/s3_main.html",_T('_menu','amazon'),"1",_T('_menu','amazon'),"1","1","1","1");
APP_INFO[6] = new Array("google_drive","icon_google_drive","/web/index.html?id=google_drive",_T('_menu','google_drive'),"1",_T('_menu','google_drive'),"1","1","1","1");

$(function() {
	if ( ($(window).width() - 280) < 100)
		var my_width = "250 px";
	else 
		var my_width = ($(window).width() - 280) + "px";
	$("#main_menu").css('width',my_width);		
	$("#main_menu_disable").css('width',my_width);
		
	$("#addon_managemnet").click(function(){
			var sys_time = (new Date()).getTime(); 
			var my_url = '/web/management.html?id=apkg&v='+ sys_time;
			location.href = my_url;
	});
	
});

function jQuery_ContextMenu_init()
{
	$("#main_menu UL LI").contextMenu({
					menu: 'myFavoriteContextMenu'
	}, function(action, el, pos) {
//		alert(
//			'Action: ' + action + '\n\n' +
//			'Element text: ' + $(el).text() + '\n\n' + 
//			'X: ' + pos.x + '  Y: ' + pos.y + ' (relative to element)\n\n' + 
//			'X: ' + pos.docX + '  Y: ' + pos.docY+ ' (relative to document)'
//			);
			
		var show_name = $(el).text();
		
		switch (action) {
            case "delete":
               
                jConfirm('M', _T('_module','msg3'), _T('_common','message'),function(r){	//Text:You are about to remove this module?
					if(r)
					{
						 var module_name = get_app_info(3,show_name,0);
						 
						 //remove icon
						 var tag_name = "#" + module_name;
			             $(tag_name).remove();
			             
			             apkg_del(module_name);
					}
				});
               
            break;
            
            case "plus":
            	my_favorite_add(show_name);
            break;
            
             case "stop":
            	 apkg_enable($(el).text(),0);
            break; 
        }	
	});
	
	
	$("#main_menu_disable UL LI").contextMenu({
					menu: 'MyContextMenu_Disable'
	}, function(action, el, pos) {
//		alert(
//			'Action: ' + action + '\n\n' +
//			'Element text: ' + $(el).text() + '\n\n' + 
//			'X: ' + pos.x + '  Y: ' + pos.y + ' (relative to element)\n\n' + 
//			'X: ' + pos.docX + '  Y: ' + pos.docY+ ' (relative to document)'
//			);
			
		var show_name = $(el).text();
		
		switch (action) {
            case "delete":              
	            jConfirm('M', _T('_module','msg3'), _T('_common','message'),function(r){	//Text:You are about to remove this module?
					if(r)
					{
						var module_name = get_app_info(3,show_name,0);
						var tag_name = "#" + module_name.toLowerCase();
		               	$(tag_name).remove();
                            
		               	 apkg_del(module_name);
					}
				});
            break;
            
            case "start":
            	 apkg_enable($(el).text(),1);
            break;
           
        }	
	});
}

function get_app_info(compare_type,compare_str,item_id)
{
	/*
	APP_INFO[x][0] = module name
	APP_INFO[x][1] = icon name(id)
	APP_INFO[x][2] = url
	APP_INFO[x][3] = show name
	APP_INFO[x][4] = enable/disable
	APP_INFO[x][5] = element id
	APP_INFO[x][6] = module type,ex: 1 -> application 2-> add-ons
	APP_INFO[x][7] = xxx_display.png status,ex:0-> don't exist,show default icon; 1->exist
	APP_INFO[x][8] = xxx_on.png,ex:0-> don't exist,show default icon; 1->exist
	APP_INFO[x][9] = xxx_off.png,ex:0-> don't exist,show default icon; 1->exist
	*/
	var str = "";
	var my_compare_type = parseInt(compare_type);
	for(var i=0;i<APP_INFO.length;i++)
	{
		if (APP_INFO[i][my_compare_type].toString() == compare_str)
		{
			switch(parseInt(item_id))
			{
				case 0:	//module name
					str = APP_INFO[i][0].toString();
				break;
				
				case 1:	//icon name
					str = APP_INFO[i][1].toString();
				break;
				
				case 2: //url
					str = APP_INFO[i][2].toString();
				break;
				
				case 3: //show name
					str = APP_INFO[i][3].toString();
				break;
				
				case 4: //enable/disable
					str = APP_INFO[i][4].toString();
				break;
				
				case 5: //element id
					str = APP_INFO[i][5].toString();
				break;
				
				case 6: //module type,ex: 1 -> application 2-> add-ons
					str = APP_INFO[i][6].toString();
				break;
				
				case 7:
					str = APP_INFO[i][7].toString();
				break;
				
				case 8:
					str = APP_INFO[i][8].toString();
				break;
				
				case 9:
					str = APP_INFO[i][9].toString();
				break;
			}
			break;
		}
	}
	return str;
}

function go_web(id_name)
{
	var web_path = get_app_info(0,id_name,2); //get app's url			
	
	if(web_path.indexOf("http://")!= -1)
	{
		var s = web_path.split("/");
		s = s[s.length-1];
		window.open("http://" + s ,"_blank");
	}	
	else if (id_name == "webfile")
	{
		window.open(web_path,"_blank");
	}	
	else		
	{
		if ((P2P_NewWindow == 1) && (id_name == "p2p"))
		{
			window.open(web_path,"_blank");
		}
		else
		{	
			var s = web_path.split("/");
				s = s[s.length-1];
			if( s.length !="" && s !="NULL" )	//fish+ for utelnetd...(no need goto webpage
			location.replace(web_path);
		}	
	}   
}   
    
function mouse_event_init()
{
	var module_id="",html_li_id="",app_status="0";
	var re = /\./g;
	var tmp="";

	for(var i=0;i<APP_INFO.length;i++)
	{	
		for(var j=0;j<APP_INFO[i].length;j++)
		{
			switch(j)
			{
				case 0://module name
					module_id = APP_INFO[i][0].toString();
					html_li_id = "#"+APP_INFO[i][0].toString();
				break;
				
				case 4://app status,ex:enable or disable
					app_status = APP_INFO[i][4].toString();
				break;
			}//end of switch..
		}//end of for(var j=0;j<APP_INFO[i].length;j++)	
			
			$(html_li_id).mouseover(function(event){
				var tmp = this.id;
				var html_icon_id = "#icon_"+tmp.replace(re,"");
				var html_img_name = "";
				
				if ( INTERNAL_MF_Is_Buildin(this.id) == 1)	 
				{
					html_img_name ="/web/images/management/"+this.id+"_on.png";
				}
				else	//APKG
				{
					if ( get_app_info(0,this.id,8) == 1 )
						html_img_name ="/"+this.id+"/"+this.id+"_on.png";
					else
						html_img_name ="/web/images/APKG_on.png";	
				}
				
				$(html_icon_id).attr('src',html_img_name); 
				
				var html_desc_id = "#desc_"+this.id;
				$(html_desc_id).css("color","#ffffff");
			});
	
			$(html_li_id).mouseout(function(){
				var html_icon_id = "#icon_"+this.id;
				var html_img_name="";
				var module_name="";
				
				if ( INTERNAL_MF_Is_Buildin(this.id) == 1)	 //function in gui_mgr.js
				{
					html_img_name ="/web/images/management/"+this.id+"_off.png";
				}
				else
				{	
					if (get_app_info(0,this.id,4)  == 1)	//get apkg status,ex:enable/disable
					{	
//						html_img_name ="/"+this.id+"/"+this.id+"_off.png";
						
						if ( get_app_info(0,this.id,8) == 1 )
							html_img_name ="/"+this.id+"/"+this.id+"_off.png";
						else
							html_img_name ="/web/images/APKG_off.png";	
					}
					else	
					{
						if ( get_app_info(0,this.id,7) == 1 )
							html_img_name ="/"+this.id+"/"+this.id+"_display.png";	
						else
							html_img_name ="/web/images/APKG_display.png";		
					}		
				}	
				$(html_icon_id).attr('src',html_img_name); 
				
				var html_desc_id = "#desc_"+this.id;
				$(html_desc_id).css("color","#000000");
				
			});	
			
			$(html_li_id).mousedown(function(e){	
				var evt = e;
				if( evt.button == 2 )	//Mouse button in Right 
				{	
					switch(this.id)
					{	
						case "schedule_downloads":
						case "remote_backup":
						case "schedule_backups":
						case "p2p":
						case "webfile":
						case "amazon_s3":
						case "google_drive":
							$("#myFavoriteContextMenu").enableContextMenuItems('#plus');
							$("#myFavoriteContextMenu").disableContextMenuItems('#stop,#delete');
						break;
						
						case "miiicasa":
							$("#myFavoriteContextMenu").disableContextMenuItems('#start,#stop');
							$("#enableItems").attr('disabled', false);
						break;
						
						case "MyCloud":
							var my_ul_id = $(this).closest('ul').attr('id');
							if (my_ul_id == "Menu_List")
							{
								$("#myFavoriteContextMenu").disableContextMenuItems('#plus,#delete');
								$('#myFavoriteContextMenu').enableContextMenuItems('#stop');
							}
							else	//Disabled Add Ons
								$('#MyContextMenu_Disable').disableContextMenuItems('#delete');
						break;
						
						default:
							$('#myFavoriteContextMenu').enableContextMenuItems('#plus,#stop,#delete');
							$("#disableItems").attr('disabled', false);
						break;
					}	
				}
				
			});
			
			if (get_app_info(0,module_id,4) == 1)//get app's status,ex:enable or disable
			{
				$(html_li_id).click(
		    		function(){
		    			if(!chk_timeout()) return;
		    			go_web(this.id);
		    			
		    			}
		  		 );	
		  	}	 
		
	}//end of for(var i=0;i<APP_INFO.length;i++)
	
} 

function check_sort_lst(module_name)
{
	/*
		flag :
			0 -> this item exist in my favorite list;
			1 -> this item isn't exist in my favorite list;
	*/
	
	var flag = 1;
	var tmp = MODULE_SORT_LIST.toString();
	
	if ( tmp.indexOf(module_name) != -1)	flag = 0;
	
	return flag;
}

function my_favorite_del(module_name)
{
	if (module_name == "") return;
	
	var my_sort_list = "";
	var flag = 0;
	
	var msg = "module_name=" + module_name + "\n";
		msg += "MODULE_SORT_LIST = " + MODULE_SORT_LIST.toString() + "\n";
	
	for (var i=0;i<MODULE_SORT_LIST.length;i++)
	{
		if ( module_name != MODULE_SORT_LIST[i])
		{
			if (my_sort_list.length == 0)
				my_sort_list += MODULE_SORT_LIST[i];
			else
				my_sort_list += ","+MODULE_SORT_LIST[i];
		}
		else 
			flag = 1;	
	}
	
	if (flag = 1)
	{
		$.ajax({
			type: "POST",
			async: false,
			cache: false,
			url: "/cgi-bin/gui_mgr.cgi",
			data: {cmd:"GUI_myfavorite_del",f_name:module_name,f_sort_lst:my_sort_list},	
			dataType: "xml",
			success: function(xml){}
		});	
	}
}

function my_favorite_add(show_name)
{	
	var my_name = "", my_show_name = "", my_path = "";
	
	for(var i=0;i<APP_INFO.length;i++)
	{
		for(var j=0;j<APP_INFO[i].length;j++)
		{
			switch(parseInt(j))
			{
				case 0:	//module name
					my_name = APP_INFO[i][0].toString();
				break;
				
				case 2: //url
					my_path = APP_INFO[i][2].toString();
				break;
				
				case 3: //show name
					my_show_name = APP_INFO[i][3].toString();
				break;
				
			}//end of switch
		}//end of for(var j=0;j<APP_INFO[i].length;j++)
		
		
		if ( my_show_name == show_name )	
		{
			INTERNAL_MF_Add(my_name,my_show_name,my_path);
			break;
		}	
	}//end of for(var i=0;i<APP_INFO.length;i++)
}

function redefine_icon(my_url,my_showname,img_display,img_on,img_off)
{
	MIIICASA_FLAG = 1;
	
	APP_INFO  = new Array();
	APP_INFO[0] = new Array("miiicasa","icon_miiicasa",my_url,my_showname,"1",my_showname,"2",img_display,img_on,img_off);
	APP_INFO[1] = new Array("schedule_downloads","icon_schedule_downloads","/web/download_mgr/downloads_main.html",_T('_menu','ftp_http_downloads'),"1",_T('_menu','ftp_http_downloads'),"1","1","1","1");
	APP_INFO[2] = new Array("remote_backup","icon_remote_backup","/web/backup_mgr/remote_main.html",_T('_menu','remote_backups'),"1",_T('_menu','remote_backups'),"1","1","1","1");
	APP_INFO[3] = new Array("schedule_backups","icon_schedule_backups","/web/backup_mgr/local_main.html",_T('_menu','schedule_backups'),"1",_T('_menu','schedule_backups'),"1","1","1","1");
	APP_INFO[4] = new Array("p2p","icon_p2p","/web/download_mgr/p2p_main.html",_T('_menu','p2p_downloads'),"1",_T('_menu','p2p_downloads'),"1","1","1","1");
	APP_INFO[5] = new Array("webfile","icon_webfile","/web/web_file/web_file_server.html",_T('_menu','web_file_server'),"1",_T('_menu','web_file_server'),"1","1","1","1");
	APP_INFO[6] = new Array("amazon_s3","icon_amazon_s3","/web/backup_mgr/s3_main.html",_T('_menu','amazon'),"1",_T('_menu','amazon'),"1","1","1","1");
	if(GOOGLEDRIVE_FUNCTION==1)APP_INFO[7] = new Array("google_drive","icon_google_drive","/web/index.html?id=google_drive",_T('_menu','google_drive'),"1",_T('_menu','google_drive'),"1","1","1","1");
	my_application_apkg_info();
}

function my_application_apkg_info()
{
	$.ajax({
			type: "POST",
			async: false,
			cache: false,
			url: "/cgi-bin/apkg_mgr.cgi",	
			data:{cmd:'cgi_application_lst'},	
			dataType: "xml",
			success: function(xml){
				var File_Center_Flag = 0;
				var Media_Center_Flag = 0;
				var re = /\s/g;
				var msg="";
												
				$(xml).find('Item').each(function(){
					
					var module_name = $(this).find('Name').text();
					var show_name = $(this).find('ShowName').text();
					var enable = $(this).find('Enable').text();
					var user = $(this).find('User').text();
					var m_center = $(this).find('Center').text();
					var page_url = "/"+module_name+"/"+ $(this).find('URL').text();	
						
					var ele_id = show_name.replace(re, "");
					
					if ( (module_name == "miiicasa") && (parseInt(MIIICASA_FLAG) == 0))
					{
						redefine_icon(page_url,show_name,$(this).find('Icon_Disable').text(),$(this).find('Icon_MouseOver').text(),$(this).find('Icon_MouseOut').text());
						return false;
					}	
					
					if ( module_name != "miiicasa")
					{	
						var my_len = APP_INFO.length;
						APP_INFO[my_len] = new Array();		
						APP_INFO[my_len][0] = module_name;
						APP_INFO[my_len][1] = "icon_" + module_name;
						APP_INFO[my_len][2] = page_url;
						APP_INFO[my_len][3] = show_name;
						APP_INFO[my_len][4] = enable;
						APP_INFO[my_len][5] = ele_id;
						APP_INFO[my_len][6] = "2";
						APP_INFO[my_len][7] = $(this).find('Icon_Disable').text();
						APP_INFO[my_len][8] = $(this).find('Icon_MouseOver').text();
						APP_INFO[my_len][9] = $(this).find('Icon_MouseOut').text();
						
						module_name = "";
						show_name = "";
						enable = "";
						user ="";
						m_center ="";
						page_url = "";
					}	
				});
				
//				var msg = "";
//				for(var i=0;i<APP_INFO.length;i++)
//				{
//					msg += APP_INFO[i].toString()+"\n";
//				}
//				alert(msg);
			}
	});//end of $.ajax
}

function applications_list_show()
{	 
	 var html_desc = "";
	 for(var i=0;i<APP_INFO.length;i++)
	 {
	 	if(GOOGLEDRIVE_FUNCTION==0 && APP_INFO[i][0]=="google_drive") continue;
	 	
	 	html_desc = "<li id=\""+APP_INFO[i][0].toString()+"\">";
	 	
	 	//icon
	 	if ( parseInt(APP_INFO[i][6].toString()) == 1) //Build-in
	 		html_desc += "<img id=\""+APP_INFO[i][1].toString()+"\" src=\"/web/images/management/"+APP_INFO[i][0].toString()+"_off.png\">";
	 	else //APKG
	 	{	
	 		if (parseInt(APP_INFO[i][4].toString()) == 1) //APKG enable
	 		{
		 		if (parseInt(APP_INFO[i][8].toString()) == 1)
		 			html_desc += "<img id=\""+APP_INFO[i][1].toString()+"\" src=\"/"+APP_INFO[i][0].toString()+"/"+APP_INFO[i][0].toString()+"_off.png\">";
		 		else	
		 			html_desc += "<img id=\""+APP_INFO[i][1].toString()+"\" src=\"/web/images/APKG_off.png\">";
		 	}
		 	else
		 	{
		 		if (parseInt(APP_INFO[i][7].toString()) == 1)
		 			html_desc += "<img id=\""+APP_INFO[i][1].toString()+"\" src=\"/"+APP_INFO[i][0].toString()+"/"+APP_INFO[i][0].toString()+"_display.png\">";
		 		else	
		 			html_desc += "<img id=\""+APP_INFO[i][1].toString()+"\" src=\"/web/images/APKG_display.png\">";
		 	}			
		}
		
	 	//div
	 	html_desc += "<div class=\"desc\" id=\"desc_"+APP_INFO[i][0].toString()+"\">"+APP_INFO[i][3].toString()+"</div>";
	 	html_desc += "</li>";
	 	
	 	if (parseInt(APP_INFO[i][4].toString()) == 1)
			$('#Menu_List').append(html_desc);
		else	
			$('#Menu_List_Disable').append(html_desc);	
	 }
}

function my_application_init()
{
	$.ajax({
			type: "POST",
			async: false,
			cache: false,
			url: "/cgi-bin/p2p.cgi",	
			data:{cmd:'p2p_home_state'},	
			dataType: "xml",
			success: function(xml){
				var res = $(xml).find('config > result').text();		
				if (parseInt(res, 10) == 0)
					APP_INFO[3][2] = "/web/index.html?id=p2p_set";
				else
					APP_INFO[3][2] = "/web/index.html?id=p2p_downloads";
					
			}
	});//end of $.ajax
	
	applications_list_show();
	
	jQuery_ContextMenu_init();
	
	//mosuseover or mouseout
	mouse_event_init();
}
/********************************************* apkg start,stop and delete **********************************************/
function apkg_enable(show_name,f_enable)
{
	 var module_name = get_app_info(3, show_name,0);
	 
	 $.ajax({
			url: "/cgi-bin/apkg_mgr.cgi",
			type: "POST",
	        data:{cmd:'module_enable_disable',f_module_name:module_name,f_enable:f_enable,f_web:'1'},
			async: false,
			cache:false,
			dataType:"xml",
			error:function(xmlHttpRequest,error){   
				location.replace("/web/application.html");
			},
			success: function(xml)
			{
			     var res = $(xml).find('config > result').text();
				
			     if (parseInt(res) == 1)
			     {
					location.replace("/web/application.html");
			     }

		    }//end of ajax success

	 }); //end of ajax
}

function apkg_del(module_name)
{
	var f = init();
	if (f == "fail") 
	{
		jAlert( _T('_login','msg5'), _T('_common','error'));
		
		$("#popup_ok").click( function (){
			location.replace("/web/login.html");
		});
		
		return false;
	}
	
	$.ajax({
		url:"/cgi-bin/apkg_mgr.cgi",
		type:"POST",
		data:{cmd:'module_uninstall',f_module_name:module_name},
		async:false,
		cache:false,
		dataType:"xml",
		success: function(xml)
		{
		     var res = $(xml).find('config > result').text();
		     if (parseInt(res) == 1)
		     {
		     	location.replace("/web/application.html");
		     }
		     
	    }//end of ajax success
	}); //end of ajax
}


/* =====================================================================
 * COLONY EDITION - Git tile
 *
 * Adds a "Git" tile to the Applications page. Click opens a panel with
 * the SSH clone URL pattern and a link to gitweb at /git/gitweb.cgi.
 *
 * Implementation: monkey-patches applications_list_show() to inject a
 * <li> after the original render. Icons are inlined as data: URIs since
 * the firmware squashfs is read-only and bind-mounts only work for paths
 * that already exist.
 *
 * Source: github.com/MotherSphere/dns345-colony-edition
 * ===================================================================== */
(function(){
    var GIT_ICON_OFF = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIwAAACcCAYAAACtFkOlAAAEg0lEQVR42u3cf2iUdQDH8c/jPbXt1q7uvFImtNigrdgWkjL9wx+YQyKRmBQrBhNJig2mMMH+2B/7Y2rqyoQmylwZlU2jURhFUmaiNpyJ0nCFBaEoSMy1nbuNdu3pj+ih83bbc+K53fO83//d870b3Pd58X2ee56HSURE6cpINtBaXzXE9Hi3zW1dgYm2m8mwbGrZkce0ebqhidD4wEITtWhFZVbg1rXGYz1925OCAQtNhcYHFkoFzSymhFIJMAQYAgwBhgBDgCECDAGGAEOAIcAQYIgAQ4AhwBBgCDAEGCLAEGAIMAQYAgwRYAgwBBiaOZle+aJ1a6sTtu39tBMBrDDOsEy2nTwMZioUoAFMyhhAAxgCDAGGAEOAydicXmfhegxgHGMAC2AcowALYByjAQtg6B5kMgXpz003PllhpgHLZNsBA5Y7HgcMWDIejckOJVYYAgxxSJrW0v2z1q2HPM+sMLfvwHTvULfe+OQh8GlEk4kX73gIfJrQZOqVXtPLWP7/vnTuQDfd6ORXEgGGAEOAIcDMsHgIHDB3HQ1YAOMYBVgA4xgNWABDgCHAEGAIMESAIcAQYAgwBJhM614/BA4YF2EBDWBSxgIawNwxBtAAhgBDgCHAEGAyNh4CB8xdRwMWwDhGAZbU88w/FAIHKwwBhgBDgCHAEAGGAEOAIcAQYIgAQ4AhwBBgCDAEGCLAEGAIMAQYAgwBhggwBBgCDAGGAEOAIQIMAYYAQ4AhwBABhgBDgCHAEGAIMESAIcAQYAgwBBgCDBFgCDBp7vOPOrWnuUWWZTEZt2V66cuORKM60nFQvefOy5hlqHzBAr34yjrdn5UV977I4KAGBwY0Pj4un88XN3b6m+M6+vFhvdGxHzBu77MPDuly7yW9/NoGWZalrvc/1Bedn6iqtibufTV1r7KUAEb65adePbPmOc1fXCFJys3L0583b9rjHW/t0Y+nf5AkhR4Oq2XfO/bYia++1pED79mv69ZWS5IeLSrU6zu3AcaNjY6MKMfvl2VZisViKix5XIZh2OOrq1/Q8mdX6WLPOZ0/0x332fKFT+uRuXN16cJFdZ/4Xus3NUiSsv05rDBu70L3WbW37k5YIebk52tOfr6uX7ma8JlQOKxQOKyB/n6Zpqkn5z/FrySvVFxWqi07t2npqkpOSgAzdf4HclVQVKhAMBh3SCLAxJXt9ys6PGy/Hujv14OhYEp/wzAMT1+f8dQ5THFZqY4f/VLB2bM1Eo2q5+QpVW9Yb4//fvlX/R2L6Y8bNxQbi+m3vp8lSfMeK1B2zr8nt8FwWJHBIZ359js9FAopN5CngqJCwLix52te0l+jozq0r13mfaZWrlmtiuVL7fG2rTs0HInYr99sapYkNbY0q+iJEklSSXmpKpYt0eH2dzU2NqbislJtbG4CjBvL8ftV21CfdHzXwXZHh6TahvpJ/w7nMESAIcAQYGhmZd+7P9bTtz1w61rjohWVWUwL/dfbTVsim9u6AglgQENTYUkAAxqaDIskJb2R0lpfNcS0ebeJsBARpbd/AO4FW6+njLt1AAAAAElFTkSuQmCC";
    var GIT_ICON_ON  = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIwAAACcCAYAAACtFkOlAAAETUlEQVR42u3dS0gUcQDH8d8sa4fWjB6bRSKBRRakhy0qqkNeRHvQ65BGBEVgpgWVFJX0psxKehfYgw5FUEQPiix7IEUdLDIKOhR0iMA0k1YTtd1OO6m72q602c58v7fdmRV25sN//jM7u0pERNHK6G5BcYrHz+axb7veV4e04QALRWLA6G7FogfH2Go2rjSjIORI4wALhSpgoOtI4wALRYLGwWahSAIMAYYAQ4AhwBBgiABDgCHAEGAIMAQYIsAQYAgwBBgCDAGGCDAEGAIMAYYAQwQYAgwBhv6fnHZ5o4FfI+gY3yNnhAkbS0/Pk43B/AkFaAATMQbQAIYAQ4AhwBBgYrZwr7NwPQYwYWMAC2DCRgEWwISNBiyAoX+Qk00Q/az0wScjTB9g6el5wICl18sBA5aYR+NkhxIjDAGGOCT1adE+rbXqIc82I0zXHRjtHWrVDz65CbwP0cTixTtuAu8jNLF6pddpZywd14vmDrTSB52cJRFgCDAEGALMfxY3gQPmr6MBC2DCRgEWwISNBiyAIcAQYAgwBBgiwBBgCDAEGAJMrPWvbwIHjIWwgAYwEWMBDWB6jQE0gCHAEGAIMASYmI2bwAHz19GABTBhowBL5NnmB4XAwQhDgCHAEGAIMESAIcAQYAgwBBgiwBBgCDAEGAIMAYYIMAQYAgwBhgBDgCECDAGGAEOAIcAQYIgAQ4AhwBBgCDBEgCHAEGAIMAQYAgwRYAgwBBgCDAGGAEMEGAJMlDt98oLWFm6Vz+dnY9gZjNfbpN07y5SdmatZWUu0d88RtfxoCVqvoeGb6uu+yuf7GbTs5o0KzZ211LZgnHZ6syePn9fLF69VtHG1JL+OHTmr8vKLKihc3mm9TZvXMJQARqqurtHinHmamTFNkpSQkKC6L/Xm8m3F+1V5v0qSNHz4MF25dsZcdvXKLZUdPG0+nj51jiRpbOponTlXBhgr1tzULFe8Sz6fX+3tbZqQlirD+H1UXrFyiRYumq2qqmd6WPmk02unz5ispKQRev7spe7crtT2nRskSa54FyOM1Xv86KmKt+wLGiGSk0cqOXmkPnz4GPSaxES3EhPdqq2tV1ycU5OneJj02qWJk9JVfvaQ5i/IZlICmD83YEC8UseN0ZAhg+QwDBQAJnSueJe8Xq/5uLa2TkPdgyP6G4ZhyO+37/UZW81hPJ40Xb50XW73UDU1Navi7iOt27DKXP72zTu1t//Up0+f1drWpppXbyVJKaNHyeXqb85lGhoadevmPbndgzVwYIJSx40BjBXLy1+mHy0tKi05rrh+ccrJna+s7AxzedH6HWps/G4+zs/bKEk6capEaenjzflPZtZMHTpwSq2trfJMTNfho7ttsw3NA3hxiscv8R/kqXOlGQWSpF3vqw3bTnqJSS8BhgBD1gETmNQEJjlEXSe8QSMMaKgnLJ1OqzsWOMUme9cVS7dzmFArEliIiKLbL6x9QuCPH5YwAAAAAElFTkSuQmCC";

    var RED  = "#7d2333";   // Colony burgundy
    var INK  = "#2e1a14";   // Colony ink
    var SOFT = "#f7edd9";   // Colony parchment soft

    var _orig_apps_list_show = applications_list_show;
    applications_list_show = function(){
        _orig_apps_list_show.apply(this, arguments);
        if ($('#git').length > 0) return;  // idempotent

        var html = '<li id="git" style="cursor:pointer">'
                 + '<img id="icon_git" src="' + GIT_ICON_OFF + '">'
                 + '<div class="desc" id="desc_git">Git</div>'
                 + '</li>';
        $('#Menu_List').append(html);

        $('#git').mouseover(function(){
            $('#icon_git').attr('src', GIT_ICON_ON);
            $('#desc_git').css('color', RED);
        }).mouseout(function(){
            $('#icon_git').attr('src', GIT_ICON_OFF);
            $('#desc_git').css('color', INK);
        }).click(function(){
            if (typeof chk_timeout === 'function' && !chk_timeout()) return;
            colony_show_git_panel();
        }).on('contextmenu', function(e){
            e.preventDefault();
        });
    };

    window.colony_show_git_panel = function(){
        var nas_host = window.location.hostname || 'dns345';
        var ssh_url  = 'ssh://' + nas_host + '/mnt/HD/HD_a2/git/&lt;repo&gt;.git';
        var http_url = 'http://' + nas_host + '/git/gitweb.cgi';

        var body =
            '<div style="font-family:JetBrainsMono,Consolas,monospace;font-size:13px;color:' + INK + ';">'
          + '  <p style="margin:0 0 14px 0;">'
          + '    Bare repos live in <code>/mnt/HD/HD_a2/git/</code> on the NAS.'
          + '    Push / pull over SSH (root-key auth), browse over HTTP.'
          + '  </p>'
          + '  <div style="margin:0 0 6px 0;font-weight:bold;color:' + RED + ';">Clone a repo</div>'
          + '  <pre style="background:' + SOFT + ';border:1px solid ' + RED + ';'
                       + 'padding:8px 10px;margin:0 0 14px 0;border-radius:4px;'
                       + 'font-size:12px;white-space:pre-wrap;word-break:break-all;">'
                       + 'git clone ' + ssh_url + '</pre>'
          + '  <div style="margin:0 0 6px 0;font-weight:bold;color:' + RED + ';">Initialize a new bare repo</div>'
          + '  <pre style="background:' + SOFT + ';border:1px solid ' + RED + ';'
                       + 'padding:8px 10px;margin:0 0 14px 0;border-radius:4px;'
                       + 'font-size:12px;white-space:pre-wrap;word-break:break-all;">'
                       + 'ssh ' + nas_host + ' "cd /mnt/HD/HD_a2/git &amp;&amp; '
                       + 'git init --bare &lt;repo&gt;.git"</pre>'
          + '  <div style="margin:0 0 6px 0;font-weight:bold;color:' + RED + ';">Browse all repos</div>'
          + '  <p style="margin:0;"><a href="' + http_url + '" target="_blank" '
          + '   style="color:' + RED + ';text-decoration:underline;">'
          + '    ' + http_url + '</a></p>'
          + '</div>';

        if ($('#colony_git_panel').length === 0) {
            $('body').append('<div id="colony_git_panel"></div>');
        }
        $('#colony_git_panel').attr('title', 'Git Server')
                              .html(body);
        $('#colony_git_panel').dialog({
            modal: true,
            width: 560,
            resizable: false,
            buttons: {
                "Open gitweb": function(){
                    window.open(http_url, '_blank');
                },
                "Close": function(){
                    $(this).dialog("close");
                }
            }
        });
    };
})();
