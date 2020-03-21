library(latticeExtra)
library(plotrix)

setwd("D:\\Dropbox\\CWS\\PISCES\\Paper")

alldata = read.csv("MRComp_Only_Final_Spp.csv")
non_outlier_data = read.csv("MRComp_Only_Non_Outlier_Spp.csv")

nickerplot <- function(df,x_col,x,y_col,y,label_col,write_png,png_outfile){
  # this stupidly brings in the column names and the columns themselves because I don't
  # yet know how to appropriately reference by name
  
  if (write_png == TRUE){ # open the png if we passed it in
    if (exists("png_outfile")){
      png(filename = png_outfile,width=7480,height=7480,res=1000)
    }else{
      print("No filename specified - writing to workspace instead"      )
    }
  }
  
  plot.new()
  par(bg=rgb(1,1,1,1)) # white with full opacity.
  
  print("Plotting")
  plot.default(log10(y) ~ log10(x),
       xlab=Log[10] ~"Absolute Value of Area Change - " ~km^2, # X Axis label
       ylab=Log[10] ~ "Change in Centroid Location - km", # Y Axis Label
       pch=16, # filled dot for character
       col=rgb(.5,.5,.5,1),
       #xlim=c(0.0,5.5),
       ylim=c(.1,2.8)

  )
  
  axis.break(1,2.94)
  #axis.break(2,)
  
  print("Writing ablines")
  horiz_ablines(c(.5,1,1.5,2,2.5),"#77777722",2)
  vert_ablines(c(3,3.5,4,4.5,5),"#77777733",2)
  
  med_line_color <- "#888888"
  abline(v=median(log10(x)),col=med_line_color,lty=2)
  abline(b=0,a=median(log10(y)), col=med_line_color,lty=2)

  print("Labeling")
  add_labels(df,x_col,y_col,label_col,"offset_x","offset_y")
  
  #par(fig=c(0.61,.99, 0.4,.99), new=TRUE) # embed next plot at 40-99% of x dim, and 40-99% of y dim

  if (write_png == TRUE){ # open the png if we passed it in
    if (exists("png_outfile")){
      a <- dev.off() # close the file if we opened one
      while (a > 1){ # keep closing if we need to - there have been some errors...
        a <- dev.off()
        print("Shutting off extra open png device")
      }
    }
  }
} # end make_scatter function


add_labels = function(data_frame,x_col,y_col,label_col,offset_x,offset_y){
  for (i in 1:nrow(data_frame)){ # for every row - this is apparently not the best way to do this in R
    
    row <- data_frame[i,] #slicing the row out
    
    #if (exists(row[label_col])){ # if we have a label
        
      text(
          x = log10(row[x_col]),
          y = log10(row[y_col]),
          labels = row[,label_col],
          adj = c(row[,offset_x],row[,offset_y]),
          cex = .75,
      )
    #}
  }
}

write_label <- function(x_val,y_val,label,adj,cex){
  text(
    x = x_val, # add the label
    y = y_val,
    labels = label,
    adj = adj,
    cex = cex,
  )
}

horiz_ablines <- function(line_locs,col,lty){
  for (i in line_locs)
    abline(b=0,a=i,col=col,lty=lty)
}

vert_ablines <- function(line_locs,col,lty){
  for (i in line_locs)
    abline(v=i,col=col,lty=lty)
}

#nickerplot(alldata,"abs_area_change_km",alldata$abs_area_change_km,"cen_dist",alldata$cen_dist,"gen_label",TRUE,"outfile.png")

postscript(file="outfile.eps",horizontal=FALSE,onefile=FALSE)
nickerplot(alldata,"abs_area_change_km",alldata$abs_area_change_km,"cen_dist",alldata$cen_dist,"gen_label",FALSE)
dev.off()

#percent overlap plot
#nickerplot(non_outlier_data,"overlap_MR_perspective",non_outlier_data$overlap_MR_perspective,"overlap_PISCES_perspective",non_outlier_data$overlap_PISCES_perspective,"gen_label",FALSE)