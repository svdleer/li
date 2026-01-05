#!/usr/bin/perl


##################################################
#
# evexml.pl 
#
# script om XML file te genereren t.b.v. EVE LI 
#
# gemaakt op ``-04-2019 
# door: Silvester van der Leer 
# versie: 0.1
#
# GPL versie 2 is van toepassing.
#
##################################################
#
# opmerkingen:
# gecommente print opdrachten staan er voor
# debug en troubleshooting.
#
################################################e#

use strict;
use lib "/home/svdleer/scripts/lib";
use XML::Writer;
use IO::File;
use MIME::Lite;

use DBI;                                                                                                                                                     
                                                                                                                                                             
# Database config                                                                                                                                            
                                                                                                                                                             
my $dbhost            = "";     # Db host                                                                                                           
my $db                = "";        # Database                                                                                                          
my $dbuser            = "";        # Db user                                                                                                           
my $dbpass            = "";       # Db pass                                                                                                           
my $dbtable           = "";        # Db table                                                                                                          
my $db_handle;                    

# SQL related                                                                                                                                                
                                                                                                                                                             
my $rows;        
my $i;

# Vars
my $hostname;
my $pedevicecount;
my @pedevices;
my @petype;
my @peloopback;
my @pestype;
my @peport;
my @pedtcpversion;
my @pelistflags;
my @deviceipfupc;
my @ifindex;
my $network;
my @networks;
my $validate; 
my $status;
my $subject;

# Date / time 

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


sub mailreport {
if (grep /204/, $status)  { $subject = "EVE NL SOHO LI XML $datum uploaded successfully";}
else  {$subject = "EVE NL SOHO LI XML $datum NOT uploaded successfully! ";    }     
my $msg = MIME::Lite->new (
From => 'kwakernaat@gmail.com',
To => 'hanneke@gmail.com',
##To => 'securityquestions@vodafoneziggo.com',
Subject => $subject,
Type =>'multipart/mixed'
) or die "Error creating multipart container: $!\n";

my $Mail_msg = "Exporting XML...\n";
   $Mail_msg .= "\n"; 
   $Mail_msg .= "Exported $pedevicecount PE devices to XML\n";
   $Mail_msg .= "\n";
   $Mail_msg .= "XML validation status\n";
   $Mail_msg .= "$validate\n"; 
   $Mail_msg .= "\n";                                                                                                                                        
   $Mail_msg .= "Uploadstatus:\n";
   $Mail_msg .= "$status";
   $Mail_msg .= "\n";                                                                                                                                        
   $Mail_msg .= "This e-mail is sent automatically by crontab\n";                                                                                                    
my $attachment = "/home/svdleer/scripts/li/output/EVE_NL_SOHO-$datum.xml";                                                                                         

my $datafilename = "EVE_NL_SOHO-$datum.xml";                                                                                                                          
                                                                                                                                                             
### Add the text message part                                                                                                                                
$msg->attach (                                                                                                                                               
Type => 'TEXT',                                                                                                                                              
Data => $Mail_msg                                                                                                                                            
) or die "Error adding the text message part: $!\n";                                                                                                         
                                                                                                                                                             
### Add the text file                                                                                                                                        
$msg->attach (                                                                                                                                               
Encoding => 'base64',                                                                                                                                        
Type => "text/csv",                                                                                                                                          
Path => $attachment,                                                                                                                                         
Filename => $datafilename,                                                                                                                                   
Disposition => 'attachment'                                                                                                                                  
) or die "Error adding $datafilename: $!\n";                                                                                                                 
                                                                                                                                                             
### Add the text message part                                                                                                                                
$msg->attach (                                                                                                                                               
Type => 'TEXT',                                                                                                                                              
Data => $Mail_msg                                                                                                                                            
) or die "Error adding the text message part: $!\n";                                                                                                         
                                                                                                                                                             
MIME::Lite->send('smtp', 'localhost', Timeout=>60);                                                                                                          
                                                                                                                                                             
$msg->send;                                                                                                                                                  
                                                                                                                                                             
}                        
 


sub dbconnect{                                                                                                                                               
$db_handle = DBI->connect("dbi:mysql:database=".$db.                                                                                                         
                          ";host=".$dbhost.                                                                                                                  
                          ";user=".$dbuser.                                                                                                                  
                          ";password=".$dbpass)                                                                                                              
             or die "Couldn't connect to database: $DBI::errstr\n";                                                                                          
};                                                                                                                                                           
                                                                                                                                                             
sub dbclose{                                                                                                                                                 
$db_handle->disconnect;                                                                                                                                      
}       


sub getnetworks($) {
my $hostname=$_[0];
my $network;
@networks=();
my $sql = "SELECT IP_BLOCK FROM tblB2B_IP_List WHERE PE_ROUTER =\"$hostname\"";
my $statement = $db_handle->prepare($sql)
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$statement->execute()
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$rows = $statement->rows();
for ($i = 0; $i < $rows; $i++)
                                {
                                  ($network) = $statement->fetchrow_array();
                                  if (!grep /0.0.0.0\/0/, $network) { push (@networks,$network) } ;                                                                 
                                  #push (@networks, $network);                                                                                                                           
                                }                                                                                                                            
}


sub getpedevices { 
$pedevicecount=0;
my $name;
my $type;
my $lo80;
my $stype;
my $port;
my $dtcp_version;
my $list_flags;
my $ifindex;
my $sql = "select upper(name), type, lo80, stype, port, dtcp_version, list_flags, ifindex from tblB2B_PE_Routers ORDER BY name ASC;";
my $statement = $db_handle->prepare($sql)
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$statement->execute()
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$rows = $statement->rows();
for ($i = 0; $i < $rows; $i++)
                                { 
                                  ($name,$type, $lo80, $stype, $port, $dtcp_version, $list_flags, $ifindex) = $statement->fetchrow_array();
                                  if ($name ne '')  { push (@pedevices,$name);
                                                      push (@petype, $type);
                                                      push (@peloopback,$lo80);
                                                      push (@pestype, $stype);
                                                      push (@peport, $port);
                                                      push (@pedtcpversion, $dtcp_version);
                                                      push (@pelistflags, $list_flags);
                                                      # remove ^M from ifindex;
                                                      $ifindex=~ s/\r//g; 
                                                      push (@ifindex, $ifindex);
                                                      $pedevicecount++;
                                                   } 
                                  
                                }
} 



sub createxml{
my $pe;
my $counter;
my $output = IO::File->new(">/home/svdleer/scripts/li/output/EVE_NL_SOHO-$datum.xml");
my $writer = XML::Writer->new(OUTPUT => $output, DATA_MODE => 1, DATA_INDENT => 8  );
$writer->xmlDecl('UTF-8');
$writer->startTag('iaps');
$counter=0;
foreach $pe (@pedevices) {       #print "$pe $peloopback[$counter]\n"; 
                                 getnetworks($pe);
                                 $writer->startTag('iap'); 
                                 $writer->startTag('attributes');
                                 $writer->comment("indicates SII device");
                                 $writer->startTag('type');
                                 if ($petype[$counter] eq 'juniper')  { $writer->characters('1'); };
                                 if ($petype[$counter] eq 'cisco-xr') { $writer->characters('18');  }; 
                                 if ($petype[$counter] eq 'sros-md')  { $writer->characters('65');  };  
                                 $writer->endTag('type');
                                 $writer->startTag('name');
                                 $writer->characters($pe);
                                 $writer->endTag('name');
                                 $writer->startTag('ipaddress');
                                 $writer->characters($peloopback[$counter]);
                                 $writer->endTag('ipaddress');
                                 if ($petype[$counter] eq 'sros-md') {  $writer->startTag('port');
                                                                        $writer->characters('830');
                                                                        $writer->endTag('port');
                                                                        $writer->startTag('li_source');
                                                                        $writer->characters('LI_MIRROR');
                                                                        $writer->endTag('li_source');
                                                                      }                          
                                 if ($petype[$counter] eq 'cisco-xr') { 
                                                                        $writer->startTag('source_interface');
                                                                        $writer->characters($ifindex[$counter]);
                                                                        $writer->endTag('source_interface');
                                                                      }  
                                 if ($petype[$counter] eq 'juniper') { 
                                                                        $writer->startTag('port');
                                                                        $writer->characters($peport[$counter]);
                                                                        $writer->endTag('port');
                                                                        $writer->startTag('dtcp_version');                                                                     
                                                                        $writer->characters($pedtcpversion[$counter]); 
                                                                        $writer->endTag('dtcp_version');
                                                                        $writer->startTag('list_flags');                                                                       
                                                                        $writer->characters($pelistflags[$counter]);                                                           
                                                                        $writer->endTag('list_flags');  
                                                                      }
                                 $writer->endTag('attributes');
                                 $writer->comment("optional");
                                 $writer->startTag('groups');
                                 $writer->comment("IAP group identifier");
                                 $writer->startTag('group');
                                 $writer->characters('3');
                                 $writer->endTag('group');
                                 $writer->endTag('groups');
                                 $writer->startTag('networks');
                                 foreach $network(@networks) { 
                                                                   if ($petype[$counter] ne 'sros-md') { 
                                                                                                         $writer->startTag('network'); 
                                                                                                         $writer->startTag('address');
                                                                                                         $writer->characters($network);
                                                                                                         $writer->endTag('address');
                                                                                                         $writer->endTag('network');
                                                                                                       } 
                                                                   if ($petype[$counter] eq 'sros-md') { print "$network\n"; 
                                                                                                         if (!grep /2001/, $network) { 
                                                                                                                                        $writer->startTag('network');
                                                                                                                                        $writer->startTag('address'); 
                                                                                                                                        $writer->characters($network); 
                                                                                                                                        $writer->endTag('address');
                                                                                                                                        $writer->startTag('attributes'); 
                                                                                                                                        $writer->startTag('ingress_index');
                                                                                                                                        $writer->characters("1");
                                                                                                                                        $writer->endTag('ingress_index');
                                                                                                                                        $writer->startTag('egress_index');
                                                                                                                                        $writer->characters("1");
                                                                                                                                        $writer->endTag('egress_index');
                                                                                                                                        $writer->endTag('attributes');
                                                                                                                                        $writer->endTag('network');
                                                                                                                                        $writer->startTag('network');
                                                                                                                                        $writer->startTag('address');
                                                                                                                                        $writer->characters($network);
                                                                                                                                        $writer->endTag('address');
                                                                                                                                        $writer->startTag('attributes');
                                                                                                                                        $writer->startTag('ingress_index');
                                                                                                                                        $writer->characters("2");
                                                                                                                                        $writer->endTag('ingress_index');
                                                                                                                                        $writer->startTag('egress_index');
                                                                                                                                        $writer->characters("1");
                                                                                                                                        $writer->endTag('egress_index');
                                                                                                                                        $writer->endTag('attributes');
                                                                                                                                        $writer->endTag('network');
                                                                                                                                     } 
                                                                                                        if (grep /2001/, $network) {
                                                                                                                                        $writer->startTag('network');
                                                                                                                                        $writer->startTag('address');
                                                                                                                                        $writer->characters($network);
                                                                                                                                        $writer->endTag('address');
                                                                                                                                        $writer->startTag('attributes');
                                                                                                                                        $writer->startTag('ingress_index');
                                                                                                                                        $writer->characters("1");
                                                                                                                                        $writer->endTag('ingress_index');
                                                                                                                                        $writer->startTag('egress_index');
                                                                                                                                        $writer->characters("1");
                                                                                                                                        $writer->endTag('egress_index');
                                                                                                                                        $writer->endTag('attributes');
                                                                                                                                        $writer->endTag('network');
                                                                                                                                    }
                                                                                                        }  

                                                              } 
                                 $writer->endTag('networks');
                                 $writer->endTag('iap'); 
                                 $counter++
                               }
 
$writer->endTag('iaps');
my $xml = $writer->end();
$output->close();
#$validate =  qx(/usr/bin/xmllint --schema /home/svdleer/scripts/li/EVE_IAP_Import.xsd /home/svdleer/scripts/li/output/EVE_NL_SOHO-$datum.xml  --noout 2>&1); 
#$validate =~s /\/home\/svdleer\/scripts\/li\/output\///g;
$validate=1;
}

# Main
dbconnect;
getpedevices;
createxml;
dbclose;
if ($validate) { 
                                   $status = qx(/home/svdleer/scripts/li/upload/sohoxmlupload.pl);
                 } 
mailreport;