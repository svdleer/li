#!/usr/bin/perl
use strict;

# Add needed Libs 

use LWP::UserAgent;
use HTTP::Cookies;
use XML::Simple;
use JSON;

# Define all vars

my @temparray;
my $csrftoken;
my $sessionid;
my $cookie_jar = HTTP::Cookies->new( );
my $response;
my $xmlSimple = new XML::Simple(KeepRoot   => 1);
my $apiloginurl;
my $apipostxmlurl;
my $authentication;
my $message;
#my $cookie;


my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
$year += 1900;
$mon  += 1;
if ( length( $mday ) == 1 ) {
    $mday = "0$mday";
}
if ( length( $mon ) == 1 ) {
    $mon = "0$mon";
}
my $datum="$year$mon$mday";

# Subs
sub getCookieValue {
my $cookies = $_[0];                                                                                                                                         
my $name = $_[1];                                                                                                                                            
my $result = ();   
$cookies->scan(sub {                                                                                                                                         
                     if ($_[1] eq $name) { 
                                           $result = $_[2];
                                         } 
                   }
              );
return $result;                                                                                                                                              
}  


# Read XML
my $dataXML = do {
                   open my $fh, '<', "/home/svdleer/scripts/li/output/EVE_NL_SOHO-$datum.xml" or die "Could not open file: $!";
                   local $/;
                   <$fh>;
                 };
$dataXML =~ s/\"/\\"/g;
$dataXML =~ s/[\r\n]+//g;

                 #my $dataXML = $xmlSimple->XMLin("EVE_NL_Infra_CMTS-20200119.xml");
                 #my $jsonfromxml = encode_json($dataXML);


# UserAgent

my $ua = LWP::UserAgent->new(ssl_opts => { 
                                           verify_hostname => 0, 
                                           SSL_verify_mode => 0,
                                           cookie_jar => {},  
                                           
                                         },
                            );
# Save Cookies
$ua->cookie_jar( $cookie_jar );
$ua->timeout( 600 );
# Define Api URLS
$apiloginurl = "https://172.17.130.70:2305/api/1/accounts/actions/login/";
$apipostxmlurl = "https://172.17.130.70:2305/api/1/iaps/actions/import_xml/"; 
$authentication = '{"username": "xml_import", "password": "liar chic teheran blessed menses judea contest corinth daily carbon"}';

# Login into API
my $req = HTTP::Request->new(POST => $apiloginurl);
$req->header('content-type' => 'application/json');
$req->content($authentication);

# Api login Response

my $response = $ua->request($req);
#my $cookiestr= $ua->cookie_jar->as_string;

# Save CSRF Token

$csrftoken=getCookieValue($cookie_jar, 'csrftoken');

print $response;
if ($response->is_success) { 
                             $ua->cookie_jar->set_cookie($cookie_jar);
                             my $postxmlreq = HTTP::Request->new(POST => $apipostxmlurl);  
                             $postxmlreq->header('content-type' => 'application/json');
                             $postxmlreq->header('X-CSRFToken' => $csrftoken);
                             $postxmlreq->header('Referer' => 'https://172.17.130.70:2305');
                             my $xmlcontent = '{"iap_groups": [3],"xml" : "'.$dataXML.'"}';
                             #print "$xmlcontent\n"; 
                             $postxmlreq->content($xmlcontent);
                             my $xmlresponse = $ua->request($postxmlreq);
                             print  $xmlresponse->decoded_content;
                             print "\n";
                             print  $xmlresponse->status_line;

                           }
    else {
             die $response->status_line;
        }