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
my @vfzv4scopes;
my @vfzv6scopes;
my $hostname;
my @devicesvfz;
my @deviceipvfz;
my $vfzdevicecount;
my $scope;
my $ipv6scope;
my $validate; 
my $status;
my $subject;
my $vfzcounter;

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
if (grep /204/, $status)  {  $subject = "EVE NL Infra LI XML $datum uploaded successfully";}
else  {$subject = "EVE NL Infra LI XML $datum NOT uploaded successfully! ";    }  
my $msg = MIME::Lite->new (
From => 'kwakernaat@gmail.com',
To => 'hanneke@gmail.com',
Subject => $subject,  
Type =>'multipart/mixed'
) or die "Error creating multipart container: $!\n";

my $Mail_msg = "Exporting XML...\n";
   $Mail_msg .= "\n"; 
   $Mail_msg .= "Exported $vfzcounter VFZ CMTS devices to XML\n";
   $Mail_msg .= "\n";
   $Mail_msg .= "XML validation status\n";
   $Mail_msg .= "$validate\n"; 
   $Mail_msg .= "\n";
   $Mail_msg .= "Uploadstatus:\n"; 
   $Mail_msg .= "$status"; 
   $Mail_msg .= "\n"; 
   $Mail_msg .= "This e-mail is sent automatically by crontab\n";                                                                                                    
my $attachment = "/home/svdleer/scripts/li/output/EVE_NL_Infra_CMTS-$datum.xml";                                                                                         

my $datafilename = "EVE_NL_Infra_CMTS-_$datum.xml";                                                                                                                          
                                                                                                                                                             
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


sub getvfzv4scopes($) {
my $hostname=$_[0];
my $scope;
@vfzv4scopes=();
my $sql = "SELECT scopesnew.scope FROM scopesnew LEFT JOIN devicesnew ON scopesnew.primscope = devicesnew.primscope WHERE devicesnew.hostname =\"$hostname\"";
my $statement = $db_handle->prepare($sql)
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$statement->execute()
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$rows = $statement->rows();
for ($i = 0; $i < $rows; $i++)
                                {
                                  ($scope) = $statement->fetchrow_array();
                                  push (@vfzv4scopes,$scope);                                                                 
                                                                                                                                                             
                                }                                                                                                                            
}


sub getvfzv6scopes($) {
my $hostname=$_[0];
my $scope;
@vfzv6scopes=();
#my $sql = "SELECT prefixname FROM `ipv6scopesnew` WHERE prefixname NOT LIKE '%/40-PD' AND leased !='0' AND UPPER(`hostname` = \"$hostname\" OR `hostname` = (SELECT LOWER(CONCAT('nl-', `fupchostname`)) AS `hostname` FROM `fupcosnlookup` WHERE `cramerhostname` = \"$hostname\" LIMIT 1));";
my $sql = "SELECT prefixname FROM `ipv6scopesnew` WHERE prefixname NOT LIKE '%/40-PD' AND UPPER(`hostname` = \"$hostname\" OR `hostname` = (SELECT LOWER(CONCAT('nl-', `fupchostname`)) AS `hostname` FROM `fupcosnlookup` WHERE `cramerhostname` = \"$hostname\" LIMIT 1));";
#print $sql;
my $statement = $db_handle->prepare($sql)
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$statement->execute()
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$rows = $statement->rows();
for ($i = 0; $i < $rows; $i++)
                                {
                                  ($scope) = $statement->fetchrow_array();
                                  $scope =~ s/\-PD//g; 
                                  push (@vfzv6scopes,$scope);

                                }
}

sub getvfzdevices { 
$vfzdevicecount=0;
my $loopbackip;
my $hostname;
my $sql = "SELECT upper(hostname), loopbackip from devicesnew where active='1' GROUP BY hostname ORDER BY hostname ASC;";
my $statement = $db_handle->prepare($sql)
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$statement->execute()
    or die "Couldn't prepare query '$sql': $DBI::errstr\n";
$rows = $statement->rows();
for ($i = 0; $i < $rows; $i++)
                                {
                                  ($hostname,$loopbackip) = $statement->fetchrow_array();
                                  if ($loopbackip ne '')  { push (@devicesvfz,$hostname);
                                                            push (@deviceipvfz,$loopbackip);
                                                             $vfzdevicecount++;
                                                           } 
                                  
                                }
} 


sub createxml{
my $cmts;
my $counter;
my $output = IO::File->new(">/home/svdleer/scripts/li/output/EVE_NL_Infra_CMTS-$datum.xml");
my $writer = XML::Writer->new(OUTPUT => $output, DATA_MODE => 1, DATA_INDENT => 8  );
$writer->xmlDecl('UTF-8');
$writer->startTag('iaps');
$counter=0;
foreach $cmts (@devicesvfz) { 
                                 getvfzv4scopes($cmts);
                                 getvfzv6scopes($cmts); 
                                 $writer->startTag('iap'); 
                                 $writer->startTag('attributes');
                                 $writer->comment("indicates SII device");
                                 $writer->startTag('type');
                                 $writer->characters('18');
                                 $writer->endTag('type');
                                 $writer->startTag('name');
                                 $writer->characters($cmts);
                                 $writer->endTag('name');
                                 $writer->startTag('ipaddress');
                                 $writer->characters($deviceipvfz[$counter]);
                                 $writer->endTag('ipaddress');
                                 if (grep /CCAP1/, $cmts) { $writer->startTag('quirks');
                                                          $writer->characters('1:m');
                                                          $writer->endTag('quirks');
                                                        }
                                 #$writer->startTag('source_interface');
                                 #$writer->endTag('source_interface');
                                 $writer->endTag('attributes');
                                 $writer->comment("optional");
                                 $writer->startTag('groups');
                                 $writer->comment("IAP group identifier");
                                 $writer->startTag('group');
                                 # Disabled group 1 after SHA256 migration 
                                 #if (grep /CCAP1/, $cmts) { $writer->characters('1'); }
                                 #elsif (grep /CCAP0/, $cmts){ $writer->characters('15'); }
                                 #elsif (grep /CCAP2/, $cmts){ $writer->characters('15'); }
                                 $writer->characters('15');                          
                                 $writer->endTag('group');
                                 $writer->endTag('groups');
                                 $writer->startTag('networks');
                                 foreach $scope(@vfzv4scopes) { 
                                                                   $writer->startTag('network'); 
                                                                   $writer->startTag('address');
                                                                   $writer->characters($scope);
                                                                   $writer->endTag('address');
                                                                   $writer->endTag('network');

                                                                 } 
                                 foreach $scope(@vfzv6scopes) { 
                                                                   $writer->startTag('network');
                                                                   $writer->startTag('address');                                                             
                                                                   $writer->characters($scope);                                                              
                                                                   $writer->endTag('address');  
                                                                   $writer->endTag('network');                                                             
                                                                 } 
                                 $writer->endTag('networks');
                                 $writer->endTag('iap'); 
                                 $counter++
                              } 
 
$writer->endTag('iaps');
$vfzcounter=$counter;
my $xml = $writer->end();
$output->close();
print "$vfzcounter vfz CMTS systems exported to XML\n";
$validate =  qx(/usr/bin/xmllint --schema /home/svdleer/scripts/li/EVE_IAP_Import.xsd /home/svdleer/scripts/li/output/EVE_NL_Infra_CMTS-$datum.xml  --noout 2>&1); 
$validate =~s /\/home\/svdleer\/scripts\/li\/output\///g;
}

# Main
dbconnect;
getvfzdevices;
createxml;
dbclose;
$status = qx(/home/svdleer/scripts/li/upload/infraxmlupload.pl); 
print $status;
mailreport;
sleep(300);
$status = qx(/home/svdleer/scripts/li/upload/reconfigure.pl);
print $status;