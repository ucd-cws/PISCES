
$(window).load(function() {
	var data = getdata("refresh");
	console.log(data);
	loaddata(data);

});

function loaddata(data) {
	$('#datatable').dynatable({
		dataset: {
			records: data
		}
	});
}

function httpGet(theUrl)
{
    var xmlHttp = null;

    xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

//loads returns a parsed json file
function getdata(filename) {
	if(!filename) return;
	var jsondata = $.ajax({
		type:"GET",
		cache: false,
		url: filename,
		dataType: "json",
		async: false,
	});
	//loaddata(jQuery.parseJSON(jsondata.responseText));
	return jQuery.parseJSON(jsondata.responseText);
}
